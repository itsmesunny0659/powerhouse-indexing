function doPost(e) {
  try {
    const data = JSON.parse(e.postData.contents);
    const url = data.url;
    const method = data.method || "GET";
    const headers = data.headers || {};
    const payload = data.body || null;

    const options = {
      method: method.toLowerCase(),
      headers: headers,
      muteHttpExceptions: true
    };
    
    if (payload && (method.toUpperCase() === 'POST' || method.toUpperCase() === 'PUT')) {
      options.payload = payload;
    }

    const response = UrlFetchApp.fetch(url, options);
    const responseHeaders = response.getAllHeaders();
    
    // Convert headers to string to pass back easily
    const outHeaders = {};
    for (let key in responseHeaders) {
       outHeaders[key] = responseHeaders[key];
    }

    return ContentService.createTextOutput(response.getContentText())
      .setMimeType(ContentService.MimeType.JSON);
      
  } catch (error) {
    return ContentService.createTextOutput(JSON.stringify({ error: error.toString() }))
      .setMimeType(ContentService.MimeType.JSON);
  }
}

function doGet(e) {
  return ContentService.createTextOutput("V2 Proxy Active (Use POST with JSON payload)");
}
