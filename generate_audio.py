import json
import os
import re
import asyncio
import edge_tts

# 核心配置
VOICE = "en-US-JennyNeural"
AUDIO_ROOT = "audio"
CARDS_FILE = "cards.json"

def clean_text_for_tts(text: str) -> str:
    """去除 HTML 标签与多余空白，保留纯净英文用于语音合成"""
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

async def generate_card_audio(card, semaphore):
    async with semaphore:
        card_id = card.get("id")
        # 提取期数，标准化为 issue01, issue02 ...
        issue_raw = str(card.get("issue", "01")).strip()
        issue_folder = f"issue{issue_raw.zfill(2)}" if not issue_raw.startswith("issue") else issue_raw
        
        # 自动创建目标子文件夹：audio/issue01/ 或 audio/issue02/
        target_dir = os.path.join(AUDIO_ROOT, issue_folder)
        os.makedirs(target_dir, exist_ok=True)
        
        # 音频完整路径：audio/issue01/1.mp3 或 audio/issue02/14.mp3
        filename = f"{card_id}.mp3"
        filepath = os.path.join(target_dir, filename)

        # 增量检测：文件已存在且大于0字节则跳过
        if os.path.exists(filepath) and os.path.getsize(filepath) > 0:
            print(f"⏩ [跳过] {issue_folder}/{filename} 音频已存在")
            return

        text = clean_text_for_tts(card.get("back", ""))
        if not text:
            print(f"⚠️ [跳过] ID {card_id} 没有有效的英文文本")
            return

        print(f"🎙️ [生成中] {issue_folder}/{filename} -> {text[:30]}...")
        try:
            communicate = edge_tts.Communicate(text, VOICE)
            await communicate.save(filepath)
            print(f"✅ [成功] {issue_folder}/{filename} 生成完毕")
        except Exception as e:
            print(f"❌ [错误] ID {card_id} 合成失败: {e}")

async def main():
    if not os.path.exists(CARDS_FILE):
        print(f"❌ 找不到 {CARDS_FILE}")
        return

    with open(CARDS_FILE, "r", encoding="utf-8") as f:
        cards = json.load(f)

    # 限制并发数为 3
    semaphore = asyncio.Semaphore(3)
    tasks = [generate_card_audio(card, semaphore) for card in cards]
    
    await asyncio.gather(*tasks)
    print("\n🎉 全部期数音频增量检查与生成完成！")

if __name__ == "__main__":
    asyncio.run(main())
