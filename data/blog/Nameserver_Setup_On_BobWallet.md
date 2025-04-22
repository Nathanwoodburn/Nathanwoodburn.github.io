
Setting up a Nameserver for your domains held in BobWallet is needed in order to use your domains for websites or other services.
This guide will walk you through the process of setting up a nameserver using the BobWallet app.


<br>
#### Prerequisites
* [BobWallet](https://bobwallet.io) with at least 1 domain  

Once you have your domain in BobWallet, you can set up a nameserver using the HNSAU service. This is a free service that allows you to create a nameserver for your domains.  
1. Create an account at [HNSAU's free Nameserver service](https://domains.hns.au)  
2. In the Add Site section, enter your domain name. Ensure you don't include any protocols (http:// or https://), subdomains (www.), or trailing slashes (/).  
3. You should now see your domain listed in the External Domains section.  
4. Click on the manage button next to the domain name to view its details.  Keep this page open, as you will need to copy the nameserver and DS info later.  
5. In BobWallet, go to Domain Manger and select the domain you want to set up a nameserver for.  
6. In the Records section for the domain, remove any existing records with TYPE NS or DS.  
7. Click on the Add Record button and select the TYPE NS.  Add the NS value from the HNSAU page. Make sure you include the trailing dot (.) at the end of the nameserver. Repeat this for all the Nameservers listed on the HNSAU page.  
   - ns1.australia.  
   - ns2.australia.   
8. Click on the Add Record button again and select the TYPE DS.  Add the DS value from the DNSSEC section in HNSAU. This DS value is unique to each domain and is used to verify the authenticity of the nameserver.  
9. Submit the changes and wait for the DNS records to propagate onchain. This will take up to 7 hrs (depending on the next tree update).  
10. You can now use the HNSAU nameserver to point your domain to any website or service.
    




[View demonstration video](https://youtu.be/Ong8A7FDH24)