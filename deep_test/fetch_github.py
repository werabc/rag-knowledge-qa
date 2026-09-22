"""带重试地从 GitHub raw 拉取真实语料到 deep_test/corpus（网络抖动对策：每文件最多重试8次）。"""
import os
import sys
import time
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "corpus")
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) rag-deep-test/1.0"}

FILES = [
    ("HarborLibrary/Chinese-History/master", "孔飞力：叫魂——1768年中国妖术大恐慌.txt", "叫魂.md", 100000),
    ("HarborLibrary/Chinese-History/master", "黄仁宇：万历十五年.txt", "万历十五年.md", 100000),
    ("HarborLibrary/Chinese-History/master", "吴思：潜规则——中国历史中的真实游戏.txt", "潜规则.md", 100000),
    ("HarborLibrary/Chinese-History/master", "钱穆：中国历代政治得失.txt", "历代政治得失.md", 100000),
    ("HarborLibrary/Chinese-History/master", "吴思：血酬定律——中国历史中的生存游戏 (2009版).txt", "血酬定律2009.md", 80000),
    ("HarborLibrary/Chinese-History/master", "吴思：血酬定律——中国历史中的生存游戏 (2003版).txt", "血酬定律2003.md", 80000),
    ("xiaobaiTech/golangFamily/main", "README.md", "golang面试题.md", 90000),
    ("jwasham/coding-interview-university/main", "README.md", "interview-en.md", 60000),
]


def fetch(url, tries=8):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            return urllib.request.urlopen(req, timeout=90).read()
        except Exception as e:
            print(f"  retry{i + 1} {url[:60]}… {type(e).__name__}: {e}", flush=True)
            time.sleep(3 + i * 2)
    return None


def main():
    os.makedirs(OUT, exist_ok=True)
    ok, fail = 0, 0
    for repo, path, out, cap in FILES:
        dest = os.path.join(OUT, out)
        if os.path.exists(dest) and os.path.getsize(dest) > 10000:
            print(f"= 已有 {out}，跳过")
            ok += 1
            continue
        url = "https://raw.githubusercontent.com/" + repo + "/" + urllib.parse.quote(path)
        raw = fetch(url)
        if raw is None:
            print(f"✗ {out}: 全部重试失败")
            fail += 1
            continue
        text = None
        for enc in ("utf-8", "gb18030"):
            try:
                text = raw.decode(enc)
                break
            except (UnicodeDecodeError, LookupError):
                continue
        if text is None:
            text = raw.decode("utf-8", "replace")
        cut = text.rfind("\n\n", 0, cap)
        text = text[:cut] if cut > 10000 else text[:cap]
        with open(dest, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"✓ {out}: {len(text)} 字符", flush=True)
        ok += 1
    print(f"完成：成功 {ok} / 失败 {fail}")
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
