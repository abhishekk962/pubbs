//selecting all required elements
const dropArea = document.querySelector(".drag-area"),
dragText = dropArea.querySelector("header"),
button = dropArea.querySelector("button"),
input = dropArea.querySelector("input");
let file; //this is a global variable and we'll use it inside multiple functions

button.onclick = ()=>{
  input.click(); //if user click on the button then the input also clicked
}

input.addEventListener("change", function(){
  //getting user select file and [0] this means if user select multiple files then we'll select only the first one
  file = this.files[0];
  dropArea.classList.add("active");
  showFile(); //calling function
});


//If user Drag File Over DropArea
dropArea.addEventListener("dragover", (event)=>{
  event.preventDefault(); //preventing from default behaviour
  dropArea.classList.add("active");
  dragText.textContent = "Release to Upload File";
});

//If user leave dragged File from DropArea
dropArea.addEventListener("dragleave", ()=>{
  dropArea.classList.remove("active");
  dragText.textContent = "Drag & Drop to Upload File";
});

//If user drop File on DropArea
dropArea.addEventListener("drop", (event)=>{
  event.preventDefault(); //preventing from default behaviour
  //getting user select file and [0] this means if user select multiple files then we'll select only the first one
  file = event.dataTransfer.files[0];
  showFile(); //calling function
});

function showFile(){
    let fileType = file.type;
    let validExtensions = ["image/jpeg", "image/jpg", "image/png","application/x-python-code", "text/csv"];
    if(validExtensions.includes(fileType)){
      let fileReader = new FileReader();
      fileReader.onload = ()=>{
        let fileURL = fileReader.result;
        let fileTag;
        if(fileType.includes('image')) {
          fileTag = `<img src="${fileURL}" alt="image">`;
        } else if(fileType === 'application/x-python-code') {
          fileTag = `<pre><code>${fileReader.result}</code></pre>`;
        } else if(fileType === 'text/csv') {
          fileTag = `<table>${parseCSV(fileReader.result)}</table>`;
        }
        dropArea.innerHTML = fileTag;
      }
      fileReader.readAsDataURL(file);
    } else {
      alert("This is not a Valid File Extension!");
      dropArea.classList.remove("active");
      dragText.textContent = "Drag & Drop to Upload File";
    }
  }

function parseCSV(csvData) {
    const lines = csvData.split('\n');
    let html = '';
    lines.forEach(line => {
      const columns = line.split(',');
      html += '<tr>';
      columns.forEach(column => {
        html += `<td>${column}</td>`;
      });
      html += '</tr>';
    });
    return html;
}
  