from docx import Document
from docx.table import Table
from docx.text.paragraph import Paragraph

def iter_block_items(parent):
    """
    Yield each paragraph and table child within parent, in document order.
    """
    for child in parent.element.body.iterchildren():
        if child.tag.endswith('}p'):
            yield Paragraph(child, parent)
        elif child.tag.endswith('}tbl'):
            yield Table(child, parent)

# Load your Word document
doc = Document('your_document.docx')

# List to keep track of all block items
block_items = list(iter_block_items(doc))

# Specify how many lines above the table you want to retrieve
num_lines = 3

# Iterate over the block items
for idx, item in enumerate(block_items):
    if isinstance(item, Table):
        # Collect paragraphs above the table
        lines_above = []
        for i in range(1, num_lines + 1):
            prev_idx = idx - i
            if prev_idx >= 0:
                prev_item = block_items[prev_idx]
                if isinstance(prev_item, Paragraph):
                    text = prev_item.text.strip()
                    if text:
                        lines_above.insert(0, text)  # Insert at the beginning
            else:
                break  # Reached the start of the document
        if lines_above:
            print(f"Lines above Table {idx + 1}:")
            for line in lines_above:
                print(line)
            print("\n")
        else:
            print(f"No text found above Table {idx + 1}.\n")
