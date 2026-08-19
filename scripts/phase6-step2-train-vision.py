#!/usr/bin/env python3
"""Train G1 native vision with stage-correct semantic grounding.

Only visual parameters update. The shared text Transformer remains frozen. Pixel
examples have independently known targets. Raw visual patch content is grounded to
one canonical direction-invariant ABC concept source embedding. After the shared
Transformer encoder has mixed in the separate visual direction token, encoded visual
content is grounded and contrastively separated in the corresponding direction-
specific frozen text-memory space that the decoder already knows how to consume.
"""
from __future__ import annotations

from hashlib import sha256
from importlib.machinery import SourceFileLoader
from importlib.util import module_from_spec, spec_from_loader
from pathlib import Path
import argparse
import json
import random
import sys

import torch
from torch.nn import functional as F

ROOT = Path(__file__).resolve().parent.parent


def load(name: str, path: Path):
    loader = SourceFileLoader(name, str(path)); spec = spec_from_loader(name, loader)
    if spec is None: raise RuntimeError(f"cannot load {path}")
    module = module_from_spec(spec); sys.modules[name] = module; loader.exec_module(module); return module


def file_sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""): digest.update(chunk)
    return digest.hexdigest()


def _canonical_source(tokenizer, vision, item):
    """One direction-invariant semantic source for raw visual content."""
    target = vision.concept(item.concept)
    return tokenizer.encode_source("ABC_TO_EL", target.abc)


def _direction_source(tokenizer, vision, item):
    """Text source whose encoded memory already supports the requested output format."""
    target = vision.concept(item.concept)
    if item.direction == "IMAGE_TO_EL": return tokenizer.encode_source("ABC_TO_EL", target.abc)
    if item.direction == "IMAGE_TO_ABC": return tokenizer.encode_source("EL_TO_ABC", target.el)
    raise ValueError(f"unsupported visual direction {item.direction}")


def _collate_sources(tokenizer, vision, selected, device, source_fn):
    encoded = [source_fn(tokenizer, vision, item) for item in selected]
    length = max(len(row) for row in encoded)
    source = torch.full((len(encoded), length), tokenizer.pad_id, dtype=torch.long, device=device)
    for index, row in enumerate(encoded): source[index, :len(row)] = torch.tensor(row, dtype=torch.long, device=device)
    return source


def _semantic_text_pool(memory, padding, source_ids, tokenizer):
    """Pool concept-bearing vectors without direction/EOS/padding tokens."""
    mask = (~padding) & source_ids.ne(tokenizer.eos_id) & source_ids.ne(tokenizer.pad_id)
    if mask.size(1): mask[:, 0] = False
    empty = ~mask.any(dim=1)
    if bool(empty.any().item()):
        fallback = ~padding
        if fallback.size(1): fallback[:, 0] = False
        mask[empty] = fallback[empty]
    weights = mask.unsqueeze(-1).to(memory.dtype)
    return (memory * weights).sum(dim=1) / weights.sum(dim=1).clamp_min(1.0)


def _multi_positive_contrastive(visual_pool, text_pool, keys, temperature: float = 0.08):
    """Contrast semantic classes while preserving duplicate positives."""
    visual = F.normalize(visual_pool, dim=-1)
    text = F.normalize(text_pool, dim=-1)
    logits = (visual @ text.transpose(0, 1)) / float(temperature)
    positives = torch.tensor(
        [[left == right for right in keys] for left in keys],
        dtype=torch.bool,
        device=logits.device,
    )
    floor = torch.finfo(logits.dtype).min
    v_pos = torch.logsumexp(logits.masked_fill(~positives, floor), dim=1)
    v_all = torch.logsumexp(logits, dim=1)
    transposed = logits.transpose(0, 1)
    t_pos = torch.logsumexp(transposed.masked_fill(~positives.transpose(0, 1), floor), dim=1)
    t_all = torch.logsumexp(transposed, dim=1)
    return 0.5 * ((v_all - v_pos).mean() + (t_all - t_pos).mean())


def _stratified_batch(examples, batch_size: int, rng: random.Random, step: int):
    """Deterministically cover every concept×direction class before seeded extras.

    The held-out probe seeds are not present in `examples`; this only balances the
    existing training set so rare/hard classes cannot disappear from an optimization
    interval because of random sampling variance.
    """
    groups = {}
    for item in examples:
        groups.setdefault((item.concept, item.direction), []).append(item)
    group_keys = sorted(groups)
    size = max(1, int(batch_size))
    selected = []
    if size >= len(group_keys):
        for offset, key in enumerate(group_keys):
            bucket = groups[key]
            selected.append(bucket[(int(step) + offset) % len(bucket)])
        remaining = size - len(selected)
        if remaining:
            selected.extend(examples[index] for index in rng.choices(range(len(examples)), k=remaining))
    else:
        start = (int(step) * size) % len(group_keys)
        for offset in range(size):
            key = group_keys[(start + offset) % len(group_keys)]
            bucket = groups[key]
            selected.append(bucket[(int(step) + offset) % len(bucket)])
    rng.shuffle(selected)
    return selected


def train_grounded_visual(model, tokenizer, vision, *, minimum_steps: int, batch_size: int, seed: int, device="cpu"):
    target_device = torch.device(device); examples = vision.training_examples(); rng = random.Random(int(seed)); torch.manual_seed(int(seed))
    visual_parameters = tuple(model.vision_parameters())
    if not visual_parameters: raise RuntimeError("Forgey visual parameters unavailable")
    original = {id(parameter): bool(parameter.requires_grad) for parameter in model.parameters()}
    for parameter in model.parameters(): parameter.requires_grad_(False)
    for parameter in visual_parameters: parameter.requires_grad_(True)
    minimum_steps=max(180,int(minimum_steps)); maximum_steps=max(900,minimum_steps*2)
    optimizer = torch.optim.AdamW(visual_parameters, lr=0.003, betas=(0.9, 0.98), weight_decay=0.003)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=maximum_steps, eta_min=0.0002)
    total_losses=[]; ce_losses=[]; align_losses=[]; raw_align_losses=[]; encoded_align_losses=[]; raw_contrastive_losses=[]; encoded_contrastive_losses=[]; learning_rates=[]; final_probes=[]
    try:
        model.eval()
        for step in range(maximum_steps):
            selected=_stratified_batch(examples,int(batch_size),rng,step)
            images=torch.stack([vision.render_concept(item.concept,item.seed) for item in selected]).to(target_device)
            directions=[item.direction for item in selected]
            decoder,labels=vision._collate_targets(tokenizer,selected,target_device)
            canonical_source=_collate_sources(tokenizer,vision,selected,target_device,_canonical_source)
            direction_source=_collate_sources(tokenizer,vision,selected,target_device,_direction_source)
            optimizer.zero_grad(set_to_none=True)
            visual_source=model.visual_source(images,directions)
            logits=model._decode(visual_source,decoder,None)
            ce=F.cross_entropy(logits.reshape(-1,logits.size(-1)),labels.reshape(-1),ignore_index=-100)
            visual_memory=model.transformer.encoder(visual_source)
            with torch.no_grad():
                canonical_padding=canonical_source.eq(tokenizer.pad_id)
                canonical_embedding=model._embed(canonical_source)
                direction_memory,direction_padding=model.encode_text_memory(direction_source)

            # Stage 1 — direction-invariant pixel concept identity.
            canonical_source_pool=_semantic_text_pool(canonical_embedding,canonical_padding,canonical_source,tokenizer)
            raw_visual_pool=visual_source[:,1:,:].mean(dim=1)
            raw_cos=(1.0-F.cosine_similarity(raw_visual_pool,canonical_source_pool,dim=-1)).mean()
            raw_mse=F.mse_loss(F.normalize(raw_visual_pool,dim=-1),F.normalize(canonical_source_pool,dim=-1))
            raw_alignment=raw_cos+2.0*raw_mse
            concept_keys=[item.concept for item in selected]
            raw_contrastive=_multi_positive_contrastive(raw_visual_pool,canonical_source_pool,concept_keys)

            # Stage 2 — direction-conditioned decoder-ready memory. Here direction is
            # intentionally part of the semantic class because the encoder is supposed
            # to transform one pixel concept into a different memory for EL vs ABC output.
            direction_text_pool=_semantic_text_pool(direction_memory,direction_padding,direction_source,tokenizer)
            encoded_visual_pool=visual_memory[:,1:,:].mean(dim=1)
            encoded_cos=(1.0-F.cosine_similarity(encoded_visual_pool,direction_text_pool,dim=-1)).mean()
            encoded_mse=F.mse_loss(F.normalize(encoded_visual_pool,dim=-1),F.normalize(direction_text_pool,dim=-1))
            direction_token=(1.0-F.cosine_similarity(visual_memory[:,0,:],direction_memory[:,0,:],dim=-1)).mean()
            encoded_alignment=encoded_cos+2.0*encoded_mse+direction_token
            decoder_keys=[(item.concept,item.direction) for item in selected]
            encoded_contrastive=_multi_positive_contrastive(encoded_visual_pool,direction_text_pool,decoder_keys)

            alignment=raw_alignment+encoded_alignment
            loss=ce+2.0*raw_alignment+4.0*encoded_alignment+0.75*raw_contrastive+1.5*encoded_contrastive
            if not torch.isfinite(loss): raise RuntimeError(f"non-finite grounded vision loss at step {step+1}")
            loss.backward(); torch.nn.utils.clip_grad_norm_(visual_parameters,max_norm=1.0); optimizer.step(); scheduler.step()
            total_losses.append(float(loss.item())); ce_losses.append(float(ce.item())); align_losses.append(float(alignment.item())); raw_align_losses.append(float(raw_alignment.item())); encoded_align_losses.append(float(encoded_alignment.item())); raw_contrastive_losses.append(float(raw_contrastive.item())); encoded_contrastive_losses.append(float(encoded_contrastive.item())); learning_rates.append(float(optimizer.param_groups[0]["lr"]))
            current=step+1
            if current==1 or current%90==0:
                probes=vision.evaluate_visual_probes(model,tokenizer,target_device); exact=sum(1 for row in probes if row["exact"])
                print(f"FORGEY_VISION_GROUNDED step={current}/{maximum_steps} total={total_losses[-1]:.6f} ce={ce_losses[-1]:.6f} raw={raw_align_losses[-1]:.6f} encoded={encoded_align_losses[-1]:.6f} raw_contrast={raw_contrastive_losses[-1]:.6f} encoded_contrast={encoded_contrastive_losses[-1]:.6f} lr={learning_rates[-1]:.6f} probes={exact}/{len(probes)}",flush=True)
                if current>=minimum_steps and exact==len(probes): final_probes=probes; break
        if not final_probes: final_probes=vision.evaluate_visual_probes(model,tokenizer,target_device)
    finally:
        for parameter in model.parameters(): parameter.requires_grad_(original[id(parameter)])
    window=min(30,max(5,len(total_losses)//5)); exact=sum(1 for row in final_probes if row["exact"])
    return {
        "truth_source":"deterministic synthetic pixel scenes",
        "grounding_source":"canonical frozen Forgey ABC source embedding before encoder plus direction-conditioned frozen decoder-ready text memory after encoder",
        "provider_generated_truth_count":0,
        "unverified_self_output_truth_count":0,
        "shared_text_parameters_updated":False,
        "collapse_prevention":"direction-invariant pre-encoder concept grounding + concept-identity contrastive separation; post-encoder concept+direction contrastive separation in decoder-ready memory",
        "representation_stages":"pre-encoder concept identity; post-encoder direction-conditioned decoder memory",
        "batching_strategy":"deterministic stratified concept-direction coverage plus seeded training-only extras",
        "frozen_transformer_mode":"eval",
        "learning_rate_schedule":"cosine 0.003 -> 0.0002",
        "steps":len(total_losses),"minimum_steps":minimum_steps,"maximum_steps":maximum_steps,"batch_size":int(batch_size),
        "training_examples":len(examples),"concept_count":len(vision.CONCEPTS),"semantic_class_count":len({(item.concept,item.direction) for item in examples}),
        "early_loss":sum(total_losses[:window])/window,"late_loss":sum(total_losses[-window:])/window,
        "early_ce_loss":sum(ce_losses[:window])/window,"late_ce_loss":sum(ce_losses[-window:])/window,
        "early_alignment_loss":sum(align_losses[:window])/window,"late_alignment_loss":sum(align_losses[-window:])/window,
        "early_raw_alignment_loss":sum(raw_align_losses[:window])/window,"late_raw_alignment_loss":sum(raw_align_losses[-window:])/window,
        "early_encoded_alignment_loss":sum(encoded_align_losses[:window])/window,"late_encoded_alignment_loss":sum(encoded_align_losses[-window:])/window,
        "early_raw_contrastive_loss":sum(raw_contrastive_losses[:window])/window,"late_raw_contrastive_loss":sum(raw_contrastive_losses[-window:])/window,
        "early_encoded_contrastive_loss":sum(encoded_contrastive_losses[:window])/window,"late_encoded_contrastive_loss":sum(encoded_contrastive_losses[-window:])/window,
        "early_contrastive_loss":sum((a+b) for a,b in zip(raw_contrastive_losses[:window],encoded_contrastive_losses[:window]))/window,
        "late_contrastive_loss":sum((a+b) for a,b in zip(raw_contrastive_losses[-window:],encoded_contrastive_losses[-window:]))/window,
        "initial_learning_rate":0.003,"final_learning_rate":learning_rates[-1] if learning_rates else 0.003,
        "probe_exact_count":exact,"probe_total":len(final_probes),"probes":final_probes,
    }


def main() -> None:
    parser=argparse.ArgumentParser(); parser.add_argument("--artifact-dir",default=str(ROOT/"data"/"phase6-step2")); parser.add_argument("--steps",type=int,default=360); parser.add_argument("--batch-size",type=int,default=28); parser.add_argument("--seed",type=int,default=640260818); args=parser.parse_args()
    artifact=Path(args.artifact_dir).resolve(); tokenizer_path=artifact/"tokenizer.json"; checkpoint_path=artifact/"forgey-insta-g1.pt"; proof_path=artifact/"training-proof.json"
    for path in (tokenizer_path,checkpoint_path,proof_path):
        if not path.is_file(): raise FileNotFoundError(f"required G1 artifact missing: {path}")
    tokenizer_module=load("_p6s2vision_tokenizer",ROOT/"📚"/"✂️"); model_module=load("_p6s2vision_model",ROOT/"🧠"/"🤖"); vision=load("_p6s2vision_curriculum",ROOT/"🧠"/"👁️")
    tokenizer=tokenizer_module.ForgeyInstaTokenizer.load(tokenizer_path); model,metadata=model_module.ForgeyInstaTransformer.load_checkpoint(checkpoint_path,map_location="cpu")
    if str(metadata.get("generation"))!="G1": raise RuntimeError("native-vision parent is not G1")
    if not model.config.vision_enabled: raise RuntimeError("Forgey G1 visual branch is disabled")
    model.to(torch.device("cpu")); before_report=model.parameter_report()
    visual=train_grounded_visual(model,tokenizer,vision,minimum_steps=args.steps,batch_size=args.batch_size,seed=args.seed,device="cpu")
    if visual["provider_generated_truth_count"]!=0 or visual["unverified_self_output_truth_count"]!=0 or visual["shared_text_parameters_updated"] is not False: raise RuntimeError("native visual truth/freeze boundary violated")
    if int(visual["probe_exact_count"])!=int(visual["probe_total"]):
        for row in visual["probes"]: print("FORGEY_VISION_PROBE",json.dumps(row,ensure_ascii=False,sort_keys=True),flush=True)
        raise RuntimeError(f"held-out native visual probes not exact: {visual['probe_exact_count']}/{visual['probe_total']}")
    if float(visual["late_loss"])>=float(visual["early_loss"]): raise RuntimeError(f"grounded visual loss did not improve: {visual['early_loss']}->{visual['late_loss']}")
    text_probes={("ABC_TO_EL","rocket"):"🚀",("EL_TO_ABC","🚀"):"rocket",("ABC_TO_EL","bicycle"):"🚲",("EL_TO_ABC","🚲"):"bicycle",("ABC_TO_EL","camera"):"📷",("EL_TO_ABC","📷"):"camera",("ABC_TO_EL","key"):"🔑",("EL_TO_ABC","🔑"):"key"}
    text_rows=[]
    for (direction,source),expected in text_probes.items():
        prediction=model.greedy_generate(tokenizer,direction,source,max_new_tokens=24,device="cpu"); text_rows.append({"direction":direction,"source":source,"expected":expected,"prediction":prediction,"exact":prediction.casefold()==expected.casefold()})
    if not all(item["exact"] for item in text_rows): raise RuntimeError("native vision training did not preserve all 8 protected text probes")
    metadata.update({"vision_enabled":True,"vision_training_steps":int(visual["steps"]),"vision_training_seed":int(args.seed),"vision_truth_source":visual["truth_source"],"vision_grounding_source":visual["grounding_source"],"vision_probe_exact":f"{visual['probe_exact_count']}/{visual['probe_total']}"})
    model.save_checkpoint(checkpoint_path,metadata=metadata); proof=json.loads(proof_path.read_text(encoding="utf-8")); after_report=model.parameter_report()
    proof["vision"]={**visual,"enabled":True,"modality":"native pixels","image_size":int(model.config.vision_image_size),"patch_size":int(model.config.vision_patch_size),"visual_tokens":int(model.config.visual_token_count),"vision_parameters":int(after_report.vision_parameters),"trainable_parameters":int(after_report.trainable_parameters),"protected_text_probes":text_rows}
    proof.setdefault("g1",{})["checkpoint_sha256"]=file_sha256(checkpoint_path); proof["g1"]["native_vision_enabled"]=True; proof["g1"]["native_vision_probe_exact"]=f"{visual['probe_exact_count']}/{visual['probe_total']}"; proof["g1"]["smoke_exact_count"]=len(text_rows); proof["g1"]["smoke_total"]=len(text_rows); proof["g1"]["smoke_predictions"]=text_rows
    proof_path.write_text(json.dumps(proof,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    if before_report.trainable_parameters!=after_report.trainable_parameters: raise RuntimeError("visual grounding changed model graph size")
    print("PHASE6_STEP2_NATIVE_VISION_OK " f"params={after_report.trainable_parameters} vision_params={after_report.vision_parameters} " f"loss={visual['early_loss']:.4f}->{visual['late_loss']:.4f} contrast={visual['early_contrastive_loss']:.4f}->{visual['late_contrastive_loss']:.4f} probes={visual['probe_exact_count']}/{visual['probe_total']} text={len(text_rows)}/{len(text_rows)} provider=0",flush=True)


if __name__=="__main__": main()
