#!/usr/bin/env python3
"""
LagerPilot-Qwen Fine-Tuning Script
Fine-tunes Qwen2.5-0.5B-Instruct using LoRA for German Warehouse & § 377 HGB Goods Receipt Audit.
"""

import os
import sys
import json
import torch
from torch.utils.data import Dataset, DataLoader
from transformers import AutoTokenizer, AutoModelForCausalLM, get_cosine_schedule_with_warmup
from peft import LoraConfig, get_peft_model

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from src.config import SYSTEM_PROMPT

class WarehouseDataset(Dataset):
    def __init__(self, json_path, tokenizer, max_length=1024):
        with open(json_path, "r", encoding="utf-8") as f:
            self.data = json.load(f)
        self.tokenizer = tokenizer
        self.max_length = max_length

    def __len__(self):
        return len(self.data)

    def __getitem__(self, idx):
        item = self.data[idx]
        user_msg = item["messages"][0]["content"]
        asst_msg = item["messages"][1]["content"]

        # Build ChatML prompt
        prompt_text = (
            f"<|im_start|>system\n{SYSTEM_PROMPT}<|im_end|>\n"
            f"<|im_start|>user\n{user_msg}<|im_end|>\n"
            f"<|im_start|>assistant\n"
        )
        full_text = prompt_text + asst_msg + "<|im_end|>\n"

        prompt_ids = self.tokenizer.encode(prompt_text, add_special_tokens=False)
        full_ids = self.tokenizer.encode(full_text, add_special_tokens=False)

        if len(full_ids) > self.max_length:
            full_ids = full_ids[:self.max_length]

        input_ids = torch.tensor(full_ids, dtype=torch.long)
        labels = input_ids.clone()

        # Mask out system + user prompt tokens so loss is only calculated on assistant output
        mask_len = min(len(prompt_ids), len(labels))
        labels[:mask_len] = -100

        # Safety check: ensure we have assistant tokens to learn from
        if (labels != -100).sum() == 0:
            labels[-10:] = input_ids[-10:]

        return {
            "input_ids": input_ids,
            "labels": labels
        }

def collate_fn(batch, pad_token_id):
    max_len = max(len(x["input_ids"]) for x in batch)
    input_ids_batch = []
    labels_batch = []
    attention_mask_batch = []

    for x in batch:
        seq_len = len(x["input_ids"])
        pad_len = max_len - seq_len
        
        inp = torch.cat([x["input_ids"], torch.full((pad_len,), pad_token_id, dtype=torch.long)])
        lbl = torch.cat([x["labels"], torch.full((pad_len,), -100, dtype=torch.long)])
        attn = torch.cat([torch.ones(seq_len, dtype=torch.long), torch.zeros(pad_len, dtype=torch.long)])

        input_ids_batch.append(inp)
        labels_batch.append(lbl)
        attention_mask_batch.append(attn)

    return {
        "input_ids": torch.stack(input_ids_batch),
        "labels": torch.stack(labels_batch),
        "attention_mask": torch.stack(attention_mask_batch)
    }

def train():
    model_name = "Qwen/Qwen2.5-0.5B-Instruct"
    output_dir = "/Users/jon/Documents/privateProjects/lagerAI/models/lagerpilot_qwen"
    train_file = "/Users/jon/Documents/privateProjects/lagerAI/data/train_dataset.json"
    val_file = "/Users/jon/Documents/privateProjects/lagerAI/data/val_dataset.json"
    
    device = "mps" if torch.backends.mps.is_available() else ("cuda" if torch.cuda.is_available() else "cpu")
    print(f"--- Starting LagerPilot-Qwen Fine-Tuning on {device} ---")

    tokenizer = AutoTokenizer.from_pretrained(model_name)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    print("Loading base model...")
    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        dtype=torch.bfloat16 if device == "mps" else torch.float32,
    )

    peft_config = LoraConfig(
        r=8,
        lora_alpha=16,
        target_modules=["q_proj", "v_proj"],
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM"
    )

    model = get_peft_model(model, peft_config)
    model.to(device)
    model.print_trainable_parameters()

    # Fast, memory-efficient alignment dataset
    train_dataset = WarehouseDataset(train_file, tokenizer)
    train_dataset.data = train_dataset.data[:30]
    val_dataset = WarehouseDataset(val_file, tokenizer)
    val_dataset.data = val_dataset.data[:6]

    batch_size = 1
    grad_accum_steps = 2
    num_epochs = 2
    learning_rate = 3e-4

    train_loader = DataLoader(
        train_dataset,
        batch_size=batch_size,
        shuffle=True,
        collate_fn=lambda b: collate_fn(b, tokenizer.pad_token_id)
    )

    val_loader = DataLoader(
        val_dataset,
        batch_size=batch_size,
        shuffle=False,
        collate_fn=lambda b: collate_fn(b, tokenizer.pad_token_id)
    )

    optimizer = torch.optim.AdamW(model.parameters(), lr=learning_rate, weight_decay=0.01)
    total_steps = (len(train_loader) // grad_accum_steps) * num_epochs
    scheduler = get_cosine_schedule_with_warmup(optimizer, num_warmup_steps=int(0.1 * total_steps), num_training_steps=total_steps)

    print(f"Total training steps: {total_steps} (Epochs: {num_epochs}, Effective Batch Size: {batch_size * grad_accum_steps})")

    step_count = 0
    model.train()

    for epoch in range(1, num_epochs + 1):
        total_loss = 0.0
        accum_loss = 0.0
        print(f"\n=== Epoch {epoch}/{num_epochs} ===")

        optimizer.zero_grad()
        for i, batch in enumerate(train_loader):
            input_ids = batch["input_ids"].to(device)
            labels = batch["labels"].to(device)
            attention_mask = batch["attention_mask"].to(device)

            outputs = model(input_ids=input_ids, attention_mask=attention_mask, labels=labels)
            loss = outputs.loss / grad_accum_steps
            loss.backward()

            accum_loss += loss.item()

            if (i + 1) % grad_accum_steps == 0 or (i + 1) == len(train_loader):
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                optimizer.step()
                scheduler.step()
                optimizer.zero_grad(set_to_none=True)
                if device == "mps":
                    torch.mps.empty_cache()

                step_count += 1
                current_step_loss = accum_loss * grad_accum_steps
                total_loss += current_step_loss
                print(f"Step {step_count}/{total_steps} | Loss: {current_step_loss:.4f} | LR: {scheduler.get_last_lr()[0]:.6f}", flush=True)
                accum_loss = 0.0

        # Run Validation
        model.eval()
        val_loss = 0.0
        with torch.no_grad():
            for val_batch in val_loader:
                v_inp = val_batch["input_ids"].to(device)
                v_lbl = val_batch["labels"].to(device)
                v_attn = val_batch["attention_mask"].to(device)
                v_out = model(input_ids=v_inp, attention_mask=v_attn, labels=v_lbl)
                val_loss += v_out.loss.item()
        
        avg_val_loss = val_loss / len(val_loader)
        print(f"--- Epoch {epoch} Validation Loss: {avg_val_loss:.4f} ---", flush=True)
        if device == "mps":
            torch.mps.empty_cache()
        model.train()

    print(f"\nSaving fine-tuned model and adapter to {output_dir}...")
    os.makedirs(output_dir, exist_ok=True)
    model.save_pretrained(output_dir)
    tokenizer.save_pretrained(output_dir)
    print("Training successfully completed and artifacts saved!")

if __name__ == "__main__":
    train()
