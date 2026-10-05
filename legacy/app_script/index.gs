<!DOCTYPE html>

<html>

<head>

  <base target="_top">

  <title>Lumberfi Commission Dashboard</title>

  <style>

    body {
      font-family: Arial, sans-serif;
      margin: 0;
      background: #f5f6f8;
      color: #222;
    }

    .header {
      background: #1f2937;
      color: white;
      padding: 20px 30px;
    }

    .header h1 {
      margin: 0;
      font-size: 24px;
    }

    .header p {
      margin: 6px 0 0;
      opacity: 0.8;
    }

    .container {
      padding: 30px;
    }

    .cards {
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 20px;
      margin-bottom: 30px;
    }

    .card {
      background: white;
      padding: 20px;
      border-radius: 10px;
      box-shadow: 0 2px 8px rgba(0,0,0,0.08);
    }

    .card-title {
      color: #666;
      font-size: 14px;
    }

    .card-value {
      font-size: 28px;
      font-weight: bold;
      margin-top: 8px;
    }

    .section {
      background: white;
      padding: 20px;
      border-radius: 10px;
      margin-bottom: 20px;
    }

    .section h2 {
      margin-top: 0;
    }

    table {
      width: 100%;
      border-collapse: collapse;
    }

    th,
    td {
      padding: 10px;
      border-bottom: 1px solid #eee;
      text-align: left;
    }

    th {
      background: #f8f8f8;
    }

    .loading {
      padding: 40px;
      text-align: center;
      font-size: 18px;
    }

    .error {
      background: #fee2e2;
      color: #991b1b;
      padding: 15px;
      border-radius: 8px;
    }
    button {
  background: #1f2937;
  color: white;
  border: none;
  padding: 10px 18px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
}

button:hover {
  opacity: 0.9;
}

#adminMessage {
  margin-top: 12px;
}
  </style>

</head>

<body>

  <div class="header">

    <h1>Lumberfi Commission Dashboard</h1>

    <p id="userInfo">
      Loading user...
    </p>

  </div>

  <div class="container">

    <div id="loading" class="loading">
      Loading dashboard...
    </div>

    <div id="error"></div>

    <div id="dashboard" style="display:none;">
    <div
  id="adminSection"
  class="section"
  style="display:none;">

  <h2>Admin Controls</h2>
  <h3>Upload Deal Dump</h3>

<input
  type="file"
  id="dealFile"
  accept=".csv">

<button
  onclick="uploadDeals()"
  id="uploadButton">

  Upload Deal Dump

</button>

<p id="uploadMessage"></p>
  <p>
    Recalculate commissions and payout schedules
    using the current deal data.
  </p>
  
  <button
    onclick="recalculateCommissions()"
    id="recalculateButton">

    Recalculate Commissions

  </button>

  <p id="adminMessage"></p>

</div>

<div class="cards">

  <div class="card">
    <div class="card-title">
      Total Deals
    </div>

    <div
      class="card-value"
      id="totalDeals">
      0
    </div>
  </div>

  <div class="card">
    <div class="card-title">
      Paid to Date
    </div>

    <div
      class="card-value"
      id="paidPayouts">
      $0
    </div>
  </div>

  <div class="card">
    <div class="card-title">
      Future Payouts
    </div>

    <div
      class="card-value"
      id="futurePayouts">
      $0
    </div>
  </div>

  <div class="card">
    <div class="card-title">
      Next Payout
    </div>

    <div
      class="card-value"
      id="nextPayout">
      -
    </div>
  </div>

</div>


      <div class="section">

        <h2>Recent Payouts</h2>

        <table>

          <thead>

            <tr>
              <th>Deal ID</th>
              <th>Component</th>
              <th>Payout Date</th>
              <th>Amount</th>
            </tr>

          </thead>

          <tbody id="payoutTable">

          </tbody>

        </table>

      </div>


      <div class="section">

        <h2>Deals</h2>

        <table>

          <thead>

            <tr>
              <th>Deal ID</th>
              <th>Customer</th>
              <th>Owner</th>
              <th>ARR</th>
              <th>ARR Commission</th>
            </tr>

          </thead>

          <tbody id="dealTable">

          </tbody>

        </table>

      </div>

    </div>

  </div>


  <script>

    function loadDashboard() {

      google.script.run

        .withSuccessHandler(
          renderDashboard
        )

        .withFailureHandler(
          showError
        )

        .getDashboardData();

    }
    function uploadDeals() {

  const fileInput =
    document.getElementById("dealFile");

  const message =
    document.getElementById("uploadMessage");

  if (!fileInput.files.length) {
    message.textContent =
      "Please select a CSV file.";

    return;
  }

  const file =
    fileInput.files[0];

  const reader =
    new FileReader();

  message.textContent =
    "Uploading...";

  reader.onload = function(event) {

    const csvContent =
      event.target.result;

    google.script.run

      .withSuccessHandler(function(result) {

        message.textContent =
          result.message +
          " Deals loaded: " +
          result.dealCount;

        loadDashboard();

      })

      .withFailureHandler(function(error) {

        message.textContent =
          "Error: " +
          error.message;

      })

      .adminUploadDeals(csvContent);

  };

  reader.readAsText(file);
}

    function renderDashboard(data) {

      console.log(data);

      document.getElementById("loading")
        .style.display = "none";

      document.getElementById("dashboard")
        .style.display = "block";


      // User information

      document.getElementById("userInfo")
        .textContent =
          data.user.name +
          " | " +
          data.user.role;
          if (data.user.role === "Admin") {

  document.getElementById("adminSection")
    .style.display = "block";

}


      // Deals

      document.getElementById("totalDeals")
        .textContent =
          data.calculations.length;


      // Payout calculations

let paidPayouts = 0;
let futurePayouts = 0;

let nextPayoutAmount = null;
let nextPayoutDate = null;

const today = new Date();

today.setHours(0, 0, 0, 0);


data.payouts.forEach(payout => {

  const amount =
    Number(payout[8]) || 0;

  const payoutDate =
    new Date(payout[5]);

  payoutDate.setHours(0, 0, 0, 0);

  if (payoutDate < today) {

    paidPayouts += amount;

  } else {

    futurePayouts += amount;

  if (
    amount > 0 &&
    (
      nextPayoutDate === null ||
      payoutDate < nextPayoutDate
    )
  )   {
      nextPayoutDate = payoutDate;
      nextPayoutAmount = amount;
  }

    }

});


document.getElementById("paidPayouts")
  .textContent =
    "$" +
    paidPayouts.toFixed(2);


document.getElementById("futurePayouts")
  .textContent =
    "$" +
    futurePayouts.toFixed(2);


if (nextPayoutDate) {

  document.getElementById("nextPayout")
    .textContent =
      "$" +
      nextPayoutAmount.toFixed(2) +
      " (" +
      formatDate(nextPayoutDate) +
      ")";

} else {

  document.getElementById("nextPayout")
    .textContent = "-";

}


      // Payout table

      const payoutTable =
        document.getElementById(
          "payoutTable"
        );

      payoutTable.innerHTML = "";


      data.payouts
        .slice(0, 10)
        .forEach(payout => {

          const row =
            document.createElement("tr");

          row.innerHTML = `
            <td>${payout[0]}</td>
            <td>${payout[2]}</td>
            <td>${formatDate(payout[5])}</td>
            <td>$${Number(payout[8] || 0).toFixed(2)}</td>
          `;

          payoutTable.appendChild(row);

        });


      // Deal table

      const dealTable =
        document.getElementById(
          "dealTable"
        );

      dealTable.innerHTML = "";


      data.calculations
        .forEach(deal => {

          const row =
            document.createElement("tr");

          row.innerHTML = `
            <td>${deal[0]}</td>
            <td>${deal[2]}</td>
            <td>${deal[3]}</td>
            <td>$${Number(deal[10] || 0).toFixed(2)}</td>
            <td>$${Number(deal[14] || 0).toFixed(2)}</td>
          `;

          dealTable.appendChild(row);

        });

    }


    function formatDate(dateString) {

      if (!dateString) {
        return "-";
      }

      return new Date(dateString)
        .toLocaleDateString(
          "en-IN",
          {
            day: "2-digit",
            month: "short",
            year: "numeric"
          }
        );

    }


    function showError(error) {

      document.getElementById("loading")
        .style.display = "none";

      document.getElementById("error")
        .innerHTML =
          `<div class="error">
            ${error.message}
          </div>`;

    }


    loadDashboard();
    function recalculateCommissions() {

  const button =
    document.getElementById(
      "recalculateButton"
    );

  const message =
    document.getElementById(
      "adminMessage"
    );

  button.disabled = true;

  message.textContent =
    "Recalculating...";

  google.script.run

    .withSuccessHandler(function(result) {

      message.textContent =
        result.message;

      button.disabled = false;

      // Reload dashboard data
      loadDashboard();

    })

    .withFailureHandler(function(error) {

      message.textContent =
        "Error: " + error.message;

      button.disabled = false;

    })

    .adminRecalculate();
}
  </script>

</body>

</html>