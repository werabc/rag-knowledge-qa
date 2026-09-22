"""
生成两页中文"扫描件"PDF（纯图像、无文字层），用于 OCR 链路验收。
做法：先用文字层排版两页，再整页渲染成位图重组 PDF——文字层彻底消失，只剩像素。
用法：python -X utf8 scripts/make_scan_pdf.py [输出路径，默认 data/scan_xuanhe.pdf]
"""
import sys

import pymupdf

PAGES = [
    "玄鹤平台建设方案\n\n总投资 560 万元，由陈立担任项目总负责人。\n一期计划 2027 年 5 月上线试运行。",
    "玄鹤平台建设方案（续）\n\n二期扩容 300 个推理节点。\n年度维保费用为 90 万元，2027 年 9 月交付终验。",
]


def main(out_path: str):
    src = pymupdf.open()
    for text in PAGES:
        page = src.new_page(width=595, height=842)  # A4 @ 72dpi
        rect = pymupdf.Rect(50, 50, 545, 700)
        page.insert_textbox(rect, text, fontsize=16,
                            fontname="china-s", color=(0.1, 0.1, 0.1))
    scan = pymupdf.open()
    for i in range(src.page_count):
        pix = src[i].get_pixmap(dpi=150)
        page = scan.new_page(width=595, height=842)
        page.insert_image(pymupdf.Rect(0, 0, 595, 842), pixmap=pix)
    scan.save(out_path)
    src.close()
    scan.close()
    # 自检：确认无文字层
    doc = pymupdf.open(out_path)
    tl = [len(doc[i].get_text().strip()) for i in range(doc.page_count)]
    doc.close()
    print(f"已生成 {out_path}，{len(PAGES)} 页，各页文字层字符数={tl}（应为 0 或极小）")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "data/scan_xuanhe.pdf")
