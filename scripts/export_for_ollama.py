#!/usr/bin/env python3
"""
LagerPilot LoRA Weight Merger & GGUF / Ollama Export Utility
Merges the fine-tuned PEFT LoRA adapter with the base Qwen2.5-0.5B-Instruct model
into a standalone model for Hugging Face upload and GGUF quantization.
"""

import os
import sys
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel

BASE_MODEL = "Qwen/Qwen2.5-0.5B-Instruct"
ADAPTER_DIR = "/Users/jon/Documents/privateProjects/lagerAI/models/lagerpilot_qwen"
OUTPUT_DIR = "/Users/jon/Documents/privateProjects/lagerAI/models/lagerpilot_qwen_merged"

def export_merged_model():
    print("=" * 70)
    print("LAGERPILOT-QWEN: MERGING LORA WEIGHTS FOR OLLAMA & HUGGINGFACE")
    print("=" * 70)

    print(f"[1/4] Loading base model: {BASE_MODEL}...")
    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL)
    base_model = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL,
        torch_dtype=torch.float32,
        device_map="cpu"
    )

    print(f"[2/4] Loading LoRA adapter: {ADAPTER_DIR}...")
    lora_model = PeftModel.from_pretrained(base_model, ADAPTER_DIR)

    print("[3/4] Merging LoRA weights into base model layers...")
    merged_model = lora_model.merge_and_unload()

    print(f"[4/4] Saving standalone merged model to {OUTPUT_DIR}...")
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    merged_model.save_pretrained(OUTPUT_DIR, safe_serialization=True)
    tokenizer.save_pretrained(OUTPUT_DIR)

    print("\n✅ Merge complete!")
    print(f"Model saved to: {OUTPUT_DIR}")
    print("\nTo convert to GGUF for Ollama:")
    print("  python3 /path/to/llama.cpp/convert_hf_to_gguf.py models/lagerpilot_qwen_merged --outfile models/lagerpilot.gguf")
    print("  ollama create lagerpilot -f Modelfile")

if __name__ == "__main__":
    export_merged_model()
