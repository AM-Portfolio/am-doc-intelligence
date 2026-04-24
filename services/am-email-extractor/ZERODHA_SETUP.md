# Setting Up Zerodha Broker Extraction

The Zerodha broker template is ready and waiting for your documents. Here's how to set it up:

## Steps to Add Zerodha Support

### 1. Add Your Zerodha PDF Documents
Upload your Zerodha portfolio statement PDFs to:
```
attached_assets/zerodha/
```

### 2. Update the Extraction Logic
Edit `brokers/zerodha/extractor.py` to customize the extraction logic for Zerodha's PDF format.

The current file is a placeholder. You'll need to:
1. Examine your Zerodha PDF structure
2. Identify where holdings data is located
3. Update the extraction patterns to match Zerodha's format

### 3. Test the Extraction
Once you've updated the extraction logic:
1. Go to the home page
2. Click on "Zerodha"
3. Upload a test PDF with the password
4. Verify the extracted data is correct

### 4. Remove "Coming Soon" Badge (Optional)
If you want to remove the "Coming Soon" badge from the Zerodha card on the home page:
1. Edit `templates/index.html`
2. Remove this line from the Zerodha card section:
   ```html
   <div class="badge">Coming Soon</div>
   ```

## Need Help?
The Groww extractor in `brokers/groww/extractor.py` is a working example you can reference when building the Zerodha extractor.
