import os

def cleanSite(path:str):
    # Check if the file is sitemap.xml
    if path.endswith('sitemap.xml'):
        # Open the file
        with open(path, 'r') as f:
            # Read the content
            content = f.read()
        # Replace all .html with empty string
        content = content.replace('.html', '')
        # Write the content back to the file
        with open(path, 'w') as f:
            f.write(content)
        # Skip the file
        return
    
    # If the file is not an html file, skip it
    if not path.endswith('.html'):
        if os.path.isdir(path):
            for file in os.listdir(path):
                cleanSite(path + '/' + file)

        return

    # Open the file
    with open(path, 'r') as f:
        # Read and remove all .html
        content = f.read().replace('.html"', '"')
    # Write the cleaned content back to the file
    with open(path, 'w') as f:
        f.write(content)


for file in os.listdir('templates'):
    cleanSite('templates/' + file)