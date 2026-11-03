PDFに埋め込まれたしおりを読み出し、階層を保ったままJSONに書き出します。

python pdf_toc_extract.py 本.pdf              # 本.toc.json にこの形式で出力

python pdf_toc_extract.py 本.pdf --offset 12  # ページ番号から12を引いて出力
