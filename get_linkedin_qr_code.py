import segno

qrcode = segno.make_qr("https://www.linkedin.com/in/marcin-rzeszowski/")
qrcode.save(
    "linkedin.png",
    scale=5,
    border=1,
)

qrcode = segno.make_qr("https://github.com/mrzeszowski/graph-rag-demo")
qrcode.save(
    "github.png",
    scale=5,
    border=1,
)