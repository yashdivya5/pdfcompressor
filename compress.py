import PyPDF2
with open('input_path', 'rb') as in_file:
        reader = PyPDF2.PdfFileReader(in_file)
        writer = PyPDF2.PdfFileWriter()
        for page_num in range(reader.getNumPages()):
            page = reader.getPage(page_num)
            x_objects = page['/Resources']['/XObject'].get_object()
            for obj in x_objects:
                if x_objects[obj]['/Subtype'] == '/Image':
                    x_objects[obj].update({
                        PyPDF2.generic.NameObject("/Filter"): PyPDF2.generic.NameObject("/DCTDecode"),
                        PyPDF2.generic.NameObject("/BitsPerComponent"): PyPDF2.generic.createStringObject("/8"),
                        PyPDF2.generic.NameObject("/ColorTransform"): PyPDF2.generic.createStringObject("/0")
                    })
            writer.addPage(page)
        with open('output_path', 'wb') as out_file:
            writer.write(out_file)
input_path = "input.pdf"  
output_path = "output_compressed.pdf"  


   
