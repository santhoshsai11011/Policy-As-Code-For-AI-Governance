import pymupdf


def extract_text_from_pdf(
    pdf_path,
    output_text_path,
):
    """
    Extract text from the PDF page by page,
    save the combined text to a TXT file,
    and return the extracted text and page data.
    """

    document = pymupdf.open(
        pdf_path
    )

    print()
    print("Opening PDF with PyMuPDF...")
    print(f"Page count   : {len(document)}")

    pages = []

    for page_number, page in enumerate(
        document,
        start=1
    ):

        print()
        print(
            f"Extracting text from page "
            f"{page_number}..."
        )

        text = page.get_text(
            "text"
        ).strip()

        pages.append({
            "page_number": page_number,
            "text": text
        })

        print(
            f"Characters extracted: "
            f"{len(text)}"
        )

    document.close()

    policy_text = "\n\n".join(
        page["text"]
        for page in pages
    )

    with open(
        output_text_path,
        "w",
        encoding="utf-8"
    ) as text_file:

        text_file.write(
            policy_text
        )

    print()
    print(
        f"Policy text saved to: "
        f"{output_text_path}"
    )

    return policy_text, pages