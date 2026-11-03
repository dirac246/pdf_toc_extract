#!/usr/bin/env python3
"""PDFに埋め込まれた階層目次（しおり／アウトライン）をJSONに書き出す。

使い方:
    python pdf_toc_extract.py input.pdf                  # input.toc.json に出力
    python pdf_toc_extract.py input.pdf -o toc.json
    python pdf_toc_extract.py input.pdf --format nested  # children付きの入れ子構造で出力
    python pdf_toc_extract.py input.pdf --offset 12      # ページ番号から12を引く（本のノンブルに戻す）
    python pdf_toc_extract.py input.pdf --keep-zenkaku   # 全角空白を半角に直さない

必要なもの: PyMuPDF (pip install pymupdf)。入っていなければ pypdf で動く。
"""
import argparse
import json
import sys
from pathlib import Path

try:
    import fitz  # PyMuPDF（推奨）
except ImportError:
    fitz = None
    try:
        from pypdf import PdfReader  # 代替
    except ImportError:
        sys.exit("PyMuPDF か pypdf が必要です: pip install pymupdf")


def clean_title(title: str, keep_zenkaku: bool) -> str:
    title = title.strip()
    if not keep_zenkaku:
        title = title.replace("　", " ")
    return title


def _raw_toc_pymupdf(pdf_path: Path):
    with fitz.open(pdf_path) as doc:
        return doc.get_toc(simple=True)  # [[level, title, page], ...] page は1始まり、無効は -1


def _raw_toc_pypdf(pdf_path: Path):
    reader = PdfReader(str(pdf_path))
    out = []

    def walk(items, level):
        for item in items:
            if isinstance(item, list):      # 直前の項目の子
                walk(item, level + 1)
                continue
            try:
                page = reader.get_destination_page_number(item) + 1
            except Exception:
                page = -1
            out.append([level, item.title or "", page])

    walk(reader.outline, 1)
    return out


def read_toc(pdf_path: Path, offset: int, keep_zenkaku: bool):
    """目次を [level, title, page] のリストで返す。PyMuPDFがなければ pypdf を使う。"""
    raw = _raw_toc_pymupdf(pdf_path) if fitz else _raw_toc_pypdf(pdf_path)
    toc = []
    for level, title, page in raw:
        # 飛び先が無効な項目は null。オフセット後の0以下は前付けのページとしてそのまま残す
        page = page - offset if page is not None and page > 0 else None
        toc.append([level, clean_title(title, keep_zenkaku), page])
    return toc


def to_nested(flat):
    """[level, title, page] の平らなリストを children 付きの入れ子構造に変換する。"""
    root = {"children": []}
    stack = [(0, root)]  # (level, node)
    for level, title, page in flat:
        node = {"title": title, "page": page}
        while stack and stack[-1][0] >= level:
            stack.pop()
        parent = stack[-1][1] if stack else root
        parent.setdefault("children", []).append(node)
        stack.append((level, node))
    return root["children"]


def main(argv=None):
    p = argparse.ArgumentParser(description="PDFの目次（しおり）をJSONに書き出す")
    p.add_argument("pdf", type=Path, help="入力PDF")
    p.add_argument("-o", "--output", type=Path, help="出力JSON（省略時は <入力名>.toc.json）")
    p.add_argument("--format", choices=["flat", "nested"], default="flat",
                   help="flat: [階層, タイトル, ページ] を1行ずつ並べたリスト（既定） / nested: children付きの入れ子")
    p.add_argument("--offset", type=int, default=0,
                   help="PDFのページ番号からこの値を引いて出力する（既定 0）")
    p.add_argument("--keep-zenkaku", action="store_true",
                   help="タイトル中の全角空白を半角に直さずそのまま残す")
    p.add_argument("--stdout", action="store_true", help="ファイルではなく標準出力に書く")
    args = p.parse_args(argv)

    if not args.pdf.exists():
        sys.exit(f"ファイルが見つかりません: {args.pdf}")

    flat = read_toc(args.pdf, args.offset, args.keep_zenkaku)
    if not flat:
        sys.exit("このPDFには目次（しおり）が埋め込まれていません。")

    data = to_nested(flat) if args.format == "nested" else flat
    if args.format == "flat":
        rows = [json.dumps(r, ensure_ascii=False) for r in data]
        text = "[\n " + ",\n ".join(rows) + "\n]"
    else:
        text = json.dumps(data, ensure_ascii=False, indent=2)

    if args.stdout:
        print(text)
    else:
        out = args.output or args.pdf.with_suffix(".toc.json")
        out.write_text(text + "\n", encoding="utf-8")
        print(f"{len(flat)} 項目を書き出しました: {out}")


if __name__ == "__main__":
    main()
