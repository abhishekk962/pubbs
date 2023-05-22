const prevBtn = document.getElementById("prevBtn1");
        const nextBtn = document.getElementById("nextBtn1");
        const submitBtn = document.getElementById("submitBtn1");
        const tables = document.querySelectorAll("table");
      
      
        let currentTableIndex = 0;
      
      
        tables.forEach((table, index) => {
          if (index !== currentTableIndex) {
            table.style.display = "none";
          }
        });
      
       
        nextBtn.addEventListener("click", () => {
          
          tables[currentTableIndex].style.display = "none";
      
         
          currentTableIndex = (currentTableIndex + 1) % tables.length;
      
          
          tables[currentTableIndex].style.display = "block";
        });
      
        prevBtn.addEventListener("click", () => {
          
          tables[currentTableIndex].style.display = "none";
      
          
          currentTableIndex =
            (currentTableIndex - 1 + tables.length) % tables.length;
      
          
          tables[currentTableIndex].style.display = "block";
        });
      
        submitBtn.addEventListener("click", () => {
            console.log("submit");
         
        });


        var table = document.getElementById("table3").getElementsByTagName("tbody")[0];

for (var i = 1; i <= 15; i++) {
    var row = table.insertRow();

    for (var j = 1; j <= 15; j++) {
        var cell = row.insertCell();
        var input = document.createElement("input");
        input.type = "text";
        cell.appendChild(input);
    }
}
      