[View video tutorial](https://cloud.woodburn.au/s/n7Q3k7QyEnwygjX)


Install prerequisites:
```bash
sudo apt install libfuse2 libunbound-dev
```
  
Download latest release AppImage from SANE version of Fingertip:  
[Fingertip Github Repo](https://github.com/randomlogin/fingertip)

Make the AppImage executable:  
```bash
chmod +x Fingertip-*.AppImage
```  
Run the AppImage:  
```bash
./Fingertip-*.AppImage
```

You should see the fingertip notification icon in the system tray, right-click and select Options > Help. This should open a browser window with the Fingertip status page.  
Go to the "Manual Setup" page, download the certificate and copy the proxy pac URL.  

Open the system settings > Network > Network Proxy. Set the Method to Automatic and paste in the URL.

Next we need to import the certificate authority into your preferred browser.  
You can usually just open the settings in the browser and search for "Certificates". Then import the certificate into the "Authorities" tab and make sure you select the option to trust it for identifying websites.