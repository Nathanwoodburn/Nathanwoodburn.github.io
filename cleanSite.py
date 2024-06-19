import os

# Read all files in the templates directory
for file in os.listdir('templates'):
    # Check if the file is sitemap.xml
    if file == 'sitemap.xml':
        # Open the file
        with open('templates/sitemap.xml', 'r') as f:
            # Read the content
            content = f.read()
        # Replace all .html with empty string
        content = content.replace('.html', '')
        # Write the content back to the file
        with open('templates/sitemap.xml', 'w') as f:
            f.write(content)
        # Skip the file
        continue
    
    # If the file is not an html file, skip it
    if not file.endswith('.html'):
        continue

    # Open the file
    with open('templates/' + file, 'r') as f:
        # Read and remove all .html
        content = f.read().replace('.html"', '"')
    # Write the cleaned content back to the file
    with open('templates/' + file, 'w') as f:
        f.write(content)