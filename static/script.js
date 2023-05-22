// let searchForm = document.querySelector('.search-form');

// // document.querySelector('#search-btn').onclick = () =>{
// //   searchForm.classList.toggle('active');
// //   navbar.classList.remove('active');
// // }

// // let navbar = document.querySelector('.navbar');

// // document.querySelector('#menu-btn').onclick = () =>{
// //   navbar.classList.toggle('active');
// //   searchForm.classList.remove('active');
// // }

// // scroll spy 
// let section = document.querySelectorAll('section');
// let navLinks = document.querySelectorAll('.header .navbar a');

// window.onscroll = () =>{
//   searchForm.classList.remove('active');
//   navbar.classList.remove('active');

//   if(window.scrollY > 0){
//     document.querySelector('.header').classList.add('active');
//   }else{
//     document.querySelector('.header').classList.remove('active');
//   }

//   section.forEach(sec =>{
//     let top = window.scrollY;
//     let offset = sec.offsetTop - 200;
//     let height = sec.offsetHeight;
//     let id = sec.getAttribute('id');

//     if(top >= offset && top < offset + height){
//       navLinks.forEach(link =>{
//         link.classList.remove('active');
//         document.querySelector('.header .navbar a[href*='+id+']').classList.add('active');
//       });
//     };

//   });

// };

// window.onload = () =>{
//   if(window.scrollY > 0){
//     document.querySelector('.header').classList.add('active');
//   }else{
//     document.querySelector('.header').classList.remove('active');
//   }
// }

// var swiper = new Swiper(".home-slider", {
//   spaceBetween: 20,
//   effect: "fade",
//   loop:true,
//   navigation: {
//     nextEl: ".swiper-button-next",
//     prevEl: ".swiper-button-prev",
//   },
//   centeredSlides: true,
//   autoplay: {
//     delay: 9500,
//     disableOnInteraction: false,
//   },
// });

// var swiper = new Swiper(".products-slider", {
//   spaceBetween: 20,
//   loop:true,
//   centeredSlides: true,
//   autoplay: {
//     delay: 9500,
//     disableOnInteraction: false,
//   },
//   grabCursor:true,
//   breakpoints: {
//     0: {
//       slidesPerView: 1,
//     },
//     768: {
//       slidesPerView: 2,
//     },
//     991: {
//       slidesPerView: 3,
//     },
//   },
// });


// // Define a function to generate the route information table
// function generateTable(numServicePeriods) {
//   const tableBody = document.querySelector('#route-info-table tbody');
//   tableBody.innerHTML = ''; // Clear the table body

//   // Loop through each service period
//   for (let i = 1; i <= numServicePeriods; i++) {
//     // Get the values from the form
//     const busStopName = document.querySelector('#Bus_stop_name_' + i).value;
//     const distanceKmDn = document.querySelector('#Distance_km_DN_' + i).value;
//     const distanceKmUp = document.querySelector('#Distance_km_UP_' + i).value;

//     // Create a new row for the table
//     const row = document.createElement('tr');
//     const serialNo = document.createElement('td');
//     const stopName = document.createElement('td');
//     const distKmDn = document.createElement('td');
//     const distKmUp = document.createElement
('td');

//     // Add the values to the row
//     serialNo.textContent = i;
//     stopName.textContent = busStopName;
//     distKmDn.textContent = distanceKmDn;
//     distKmUp.textContent = distanceKmUp;

//     // Add the cells to the row
//     row.appendChild(serialNo);
//     row.appendChild(stopName);
//     row.appendChild(distKmDn);
//     row.appendChild(distKmUp);

//     // Add the row to the table
//     tableBody.appendChild(row);
//   }
// }

// // Add an event listener to the form submit button
// document.querySelector('form').addEventListener('submit', (event) => {
//   event.preventDefault(); // Prevent the form from submitting
//   const numServicePeriods = document.querySelector('#Number_of_service_periods').value;
// });


// NAV BAR FUNCTIONALITY
$(document).ready(function() {
  // set up event listeners for the navbar links
  $('.nav-link').click(function(e) {
    e.preventDefault();

    // get the form ID from the data attribute
    var formID = $(this).data('form');

    // hide all forms and show the one with the corresponding ID
    $('.form').hide();
    $('#' + formID).show();

    // set the active class on the clicked link and remove it from the others
    $('.nav-link').removeClass('active');
    $(this).addClass('active');
  });

  // set up event listeners for the form submission
  $('.form').submit(function(e) {
    e.preventDefault();

    // submit the form
    $(this).ajaxSubmit({
      success: function(responseText, statusText, xhr, $form) {
        // if the form was submitted successfully, hide it and show the next one
        $form.hide().next('.form').show();

        // update the active class on the navbar link
        $('.nav-link').removeClass('active');
        $('.nav-link[data-form="' + $form.next('.form').attr('id') + '"]').addClass('active');
      }
    });
  });


  // set up
});
// Genereate table method

function addRow(){
  // var sno = document.getElementById('sno').value;
  var Bus_route_name = document.getElementById('Bus_route_name').value;
  var distanceDN = document.getElementById('distanceDN').value;
  var distanceUP = document.getElementById('distanceUP').value;
  var table1 = document.getElementsByTagName('table')[0];
  var newRow = table1.insertRow(table1.rows.length);

  var cell1 = newRow.insertCell(0);
  var cell2 = newRow.insertCell(1);
  var cell3 = newRow.insertCell(2);

  cell1.innerHTML = Bus_route_name;
  cell2.innerHTML = distanceDN;
  cell3.innerHTML = distanceUP;
  console.log(Bus_route_name);
  console.log("j")
 
// PARAMETERS FORM NEXT FUNCTION 
const  form = document.querySelector('form')
        nextBtn = form.querySelector('.nextBtn'),
        backBtn = form.querySelector('.backBtn'),
        allInput = form.querySelectorAll('.first input')

nextBtn.addEventListener("click", () =>{
    allInput.forEach(input => {
        if(input.value != ""){
            form.classList.add('secActive');
        }else{
            form.classList.remove('secActive');
            // alert("Input is empty!!");

        }
    })
})

backBtn.addEventListener("click", () => {
    form.classList.remove('secActive')
})



  // second table generator
  var Bus_service_timings_From = document.getElementById("Bus_service_timings_From");
  var Bus_service_timings_To = document.getElementById("Bus_service_timings_To");
  var table2 = document.getElementsByTagName('table')[1]; 
  var newRow1 = table2.insertRow(table2.rows.length);

  var cell_1 = newRow1.insertCell(0);
  var cell_2 = newRow1.insertCell(1);

  cell_1.innerHTML = Bus_service_timings_From;
  cell_2.innerHTML = Bus_service_timings_To;

}





// NAVBAR CODE 
const prevBtn = document.getElementById("prevBtn");
        const nextBtn = document.getElementById("nextBtn");
        const submitBtn = document.getElementById("submitBtn");
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


// FORM default submission

// Get all form elements using querySelectorAll()
const forms = document.querySelectorAll("form");

// Loop through the forms and add an event listener for submit
forms.forEach((form) => {
  form.addEventListener("submit", (event) => {
    // Prevent default form submission behavior
    event.preventDefault();

    // Do something else
    console.log("Form submitted but prevented default behavior");
  });
});
