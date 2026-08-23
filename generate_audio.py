import json
import os
import re
import hashlib
import asyncio
import edge_tts

# 核心配置
VOICE = "en-US-JennyNeural"
AUDIO_ROOT = "audio"
CARDS_FILE = "cards.json"
MANIFEST_FILE = os.path.join(AUDIO_ROOT, ".manifest.json")

def clean_text_for_tts(text: str) -> str:
    """去除 HTML 标签与多余空白，保留纯净英文用于语音合成"""
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def get_text_hash(text: str) -> str:
    """计算英文文本的 MD5 哈希值，用于精确感知内容变更"""
    return hashlib.md5(text.encode("utf-8")).hexdigest()

async def generate_card_audio(card, manifest, new_manifest, semaphore):
    async with semaphore:
        card_id = str(card.get("id"))
        issue_raw = str(card.get("issue", "01")).strip()
        issue_folder = f"issue{issue_raw.zfill(2)}" if not issue_raw.startswith("issue") else issue_raw
        
        target_dir = os.path.join(AUDIO_ROOT, issue_folder)
        os.makedirs(target_dir, exist_ok=True)
        
        filename = f"{card_id}.mp3"
        filepath = os.path.join(target_dir, filename)

        text = clean_text_for_tts(card.get("back", ""))
        if not text:
            return

        current_hash = get_text_hash(text)
        new_manifest[f"{issue_folder}/{card_id}"] = current_hash

        # 智能检测：如果音频存在 且 文本MD5哈希未发生变化，则跳过
        if os.path.exists(filepath) and manifest.get(f"{issue_folder}/{card_id}") == current_hash:
            print(f"⏩ [无变化跳过] {issue_folder}/{filename}")
            return

        print(f"🎙️ [生成/更新中] {issue_folder}/{filename} -> {text[:30]}...")
        try:
            communicate = edge_tts.Communicate(text, VOICE)
            await communicate.save(filepath)
            print(f"✅ [就绪] {issue_folder}/{filename} 更新成功")
        except Exception as e:
            print(f"❌ [错误] ID {card_id} 合成失败: {e}")

async def main():
    if not os.path.exists(CARDS_FILE):
        print(f"❌ 找不到 {CARDS_FILE}")
        return

    os.makedirs(AUDIO_ROOT, exist_ok=True)
    manifest = {}
    if os.path.exists(MANIFEST_FILE):
        try:
            with open(MANIFEST_FILE, "r", encoding="utf-8") as f:
                manifest = json.load(f)
        except Exception:
            manifest = {}

    with open(CARDS_FILE, "r", encoding="utf-8") as f:
        cards = json.load(f)

    new_manifest = dict(manifest)
    semaphore = asyncio.Semaphore(3)
    tasks = [generate_card_audio(card, manifest, new_manifest, semaphore) for card in cards]
    
    await asyncio.gather(*tasks)

    # 保存最新的文本哈希记录
    with open(MANIFEST_FILE, "w", encoding="utf-8") as f:
        json.dump(new_manifest, f, indent=2)

    print("\n🎉 全部音频智能检查与生成完成！")

if __name__ == "__main__":
    asyncio.run(main())
