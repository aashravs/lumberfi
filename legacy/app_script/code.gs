function getDeals() {
  const spreadsheet = SpreadsheetApp.getActiveSpreadsheet(); //google apps scripts service
  const sheet = spreadsheet.getSheetByName("Deals");

  if (!sheet) {
    throw new Error("Deals sheet was not found.");
  }

  const data = sheet.getDataRange().getValues();

  const rows = data.slice(1); //remove header

  const deals = rows.map(row => ({
    dealId: row[0],
    customerId: row[1],
    customerName: row[2],
    dealName: row[3],
    dealType: row[4],
    dealOwner: row[5],
    leadSource: row[6],
    partnerName: row[7],
    closeDate: row[8],
    dealStatus: row[9],
    cancellationDate: row[10],
    tcv: row[11],
    implementationFee: row[12],
    implementationPaymentTerms: row[13],
    billingType: row[14],
    goLiveDate: row[15],
    paymentTerms: row[16]
  }));

  return deals;
}


function calculateFinancials(deal) {

  // check whether the deal is inside the Commission Plan period
  const planStart = new Date(2026, 6, 1);  // 1 July 2026
  const planEnd = new Date(2026, 8, 30);   // 30 September 2026

  const closeDate = new Date(deal.closeDate);

  const inPlan =
    closeDate >= planStart &&
    closeDate <= planEnd;


  // calculate ARR
  const arr = deal.tcv - deal.implementationFee;


  // determine the ARR commission rate
  let arrCommissionRate;

  if (deal.leadSource === "Partnership") {
    arrCommissionRate = 0.05;
  } else {
    arrCommissionRate = 0.10;
  }


  // calculate Annual ARR Commission
  const arrCommission = arr * arrCommissionRate;


  // determine whether the deal is Direct or Partner
  const channel =
    deal.leadSource === "Partnership"
      ? "Partner"
      : "Direct";


  // calculate implementation fee as % of tcv
  const implementationPercentage =
    deal.tcv === 0
      ? 0
      : deal.implementationFee / deal.tcv;


  // determine implementation commission rate
  let implementationCommissionRate = 0;

  if (implementationPercentage <= 0.10) {

    implementationCommissionRate = 0;

  } else if (implementationPercentage <= 0.20) {

    implementationCommissionRate =
      channel === "Direct" ? 0.10 : 0.05;

  } else {

    implementationCommissionRate =
      channel === "Direct" ? 0.15 : 0.10;
  }


  // calculate implementation commission.
  const implementationCommission =
    deal.implementationFee *
    implementationCommissionRate;


  return {
    dealId: deal.dealId,
    inPlan: inPlan,
    arr: arr,
    arrCommissionRate: arrCommissionRate,
    arrCommission: arrCommission,
    channel: channel,
    implementationPercentage: implementationPercentage,
    implementationCommissionRate: implementationCommissionRate,
    implementationCommission: implementationCommission
  };
}



function setupBackendSheets() {

  const spreadsheet = SpreadsheetApp.getActiveSpreadsheet();

  const requiredSheets = [
    "Users",
    "Calculations",
    "Payouts",
    "Assumption"
  ];

  requiredSheets.forEach(name => {

    let sheet = spreadsheet.getSheetByName(name);

    if (!sheet) {
      sheet = spreadsheet.insertSheet(name);
      Logger.log("Created sheet: " + name);
    } else {
      Logger.log("Already exists: " + name);
    }

  });

}
function runFinancialCalculations() {

  const spreadsheet = SpreadsheetApp.getActiveSpreadsheet();

  const calculationsSheet =
    spreadsheet.getSheetByName("Calculations");

  if (!calculationsSheet) {
    throw new Error("Calculations sheet does not exist. Run setupBackendSheets first.");
  }

  const deals = getDeals();

  const headers = [
    "Deal ID",
    "Customer ID",
    "Customer Name",
    "Deal Owner",
    "Deal Type",
    "Lead Source",
    "Close Date",
    "Deal Status",
    "TCV",
    "Implementation Fee",
    "ARR",
    "In Plan",
    "Channel",
    "ARR Commission Rate",
    "ARR Commission",
    "Implementation Fee %",
    "Implementation Commission Rate",
    "Implementation Commission",
    "Billing Type",
    "Go-Live Date",
    "Payment Terms"
  ];

  // clear previous calculation results
  calculationsSheet.clearContents();

  calculationsSheet.getRange(
    1,
    1,
    1,
    headers.length
  ).setValues([headers]);

  const output = [];

  deals.forEach(deal => {

    const result = calculateFinancials(deal);

    output.push([
      deal.dealId,
      deal.customerId,
      deal.customerName,
      deal.dealOwner,
      deal.dealType,
      deal.leadSource,
      deal.closeDate,
      deal.dealStatus,
      deal.tcv,
      deal.implementationFee,
      result.arr,
      result.inPlan,
      result.channel,
      result.arrCommissionRate,
      result.arrCommission,
      result.implementationPercentage,
      result.implementationCommissionRate,
      result.implementationCommission,
      deal.billingType,
      deal.goLiveDate,
      deal.paymentTerms
    ]);

  });

  if (output.length > 0) {

    calculationsSheet
      .getRange(
        2,
        1,
        output.length,
        headers.length
      )
      .setValues(output);

  }

  calculationsSheet.autoResizeColumns(
    1,
    headers.length
  );

  Logger.log(
    "Financial calculations completed for " +
    output.length +
    " deals."
  );
}
function addWorkingDays(date, workingDays) {
  let result = new Date(date);
  let daysAdded = 0;

  while (daysAdded < workingDays) {
    result.setDate(result.getDate() + 1);

    const day = result.getDay();

    // Monday = 1, Friday = 5
    if (day !== 0 && day !== 6) {
      daysAdded++;
    }
  }

  return result;
}


function moveToMondayIfWeekend(date) {
  const result = new Date(date);
  const day = result.getDay();

  if (day === 6) {
    // saturday -> monday
    result.setDate(result.getDate() + 2);
  } else if (day === 0) {
    // sunday -> monday
    result.setDate(result.getDate() + 1);
  }

  return result;
}


function getNextMonthDay(date, dayOfMonth) {
  return new Date(
    date.getFullYear(),
    date.getMonth() + 1,
    dayOfMonth
  );
}


function getLastFridayOfMonth(year, month) {
  // month is zero-based: January = 0, December = 11
  const lastDay = new Date(year, month + 1, 0);

  const day = lastDay.getDay();

  // Friday = 5
  const daysBack = (day - 5 + 7) % 7;

  lastDay.setDate(lastDay.getDate() - daysBack);

  return lastDay;
}

function createAnnualPayouts(deal, financials) {

  if (!financials.inPlan) {
    return [];//no commission payout is generated
  }

  const payouts = [];

  const closeDate = new Date(deal.closeDate);

  // advance

  const advanceAmount =
    financials.arrCommission * 0.25;

  const advanceDate =
    moveToMondayIfWeekend(
      getNextMonthDay(closeDate, 10)
    );

  payouts.push({
    dealId: deal.dealId,
    dealOwner: deal.dealOwner,
    component: "Advance",
    payoutDate: advanceDate,
    amount: advanceAmount
  });

  // implementation

  if (financials.implementationCommission > 0) {

    const implementationAmount =
      financials.implementationCommission;

    const signingDate =
      moveToMondayIfWeekend(
        getNextMonthDay(closeDate, 15)
      );

    if (
      deal.implementationPaymentTerms ===
      "100% at signing"
    ) {

      payouts.push({
        dealId: deal.dealId,
        dealOwner: deal.dealOwner,
        component: "Implementation",
        payoutDate: signingDate,
        amount: implementationAmount
      });

    }

    else if (
      deal.implementationPaymentTerms ===
      "50% at signing / 50% at go-live"
    ) {

      // first 50%
      const firstHalf =
        implementationAmount * 0.50;

      payouts.push({
        dealId: deal.dealId,
        dealOwner: deal.dealOwner,
        component: "Implementation - Signing",
        payoutDate: signingDate,
        amount: firstHalf
      });

      // second 50% depends on collection
      const goLiveInvoiceDate =
        new Date(deal.goLiveDate);

      const goLiveCollectionDate =
        addWorkingDays(
          goLiveInvoiceDate,
          deal.paymentTerms
        );

      let secondPayoutYear =
        goLiveCollectionDate.getFullYear();

      let secondPayoutMonth =
        goLiveCollectionDate.getMonth() + 1;

      if (secondPayoutMonth > 11) {
        secondPayoutMonth = 0;
        secondPayoutYear++;
      }

      const secondPayoutDate =
        moveToMondayIfWeekend(
          new Date(
            secondPayoutYear,
            secondPayoutMonth,
            15
          )
        );

      payouts.push({
        dealId: deal.dealId,
        dealOwner: deal.dealOwner,
        component: "Implementation - Go-Live",
        payoutDate: secondPayoutDate,
        amount: firstHalf,
        collectionDate: goLiveCollectionDate
      });
    }
  }

  // annual invoice

  let invoiceDate;

  if (deal.billingType === "Annual Subscription") {

    invoiceDate =
      new Date(deal.closeDate);

  }

  else if (
    deal.billingType ===
    "Annual - Billed on Go-Live"
  ) {

    invoiceDate =
      new Date(deal.goLiveDate);

  }

  else {

    return payouts;
  }

  const collectionDate =
    addWorkingDays(
      invoiceDate,
      deal.paymentTerms
    );

  // balance

  const balanceAmount =
    financials.arrCommission * 0.75;

  let payoutYear =
    collectionDate.getFullYear();

  let payoutMonth =
    collectionDate.getMonth() + 1;

  if (payoutMonth > 11) {
    payoutMonth = 0;
    payoutYear++;
  }

  const balanceDate =
    getLastFridayOfMonth(
      payoutYear,
      payoutMonth
    );

  payouts.push({
    dealId: deal.dealId,
    dealOwner: deal.dealOwner,
    component: "Balance",
    payoutDate: balanceDate,
    amount: balanceAmount,
    collectionDate: collectionDate
  });

  return payouts;
}

function createRecurringPayouts(deal, financials) {

  if (!financials.inPlan) {
    return [];
  }

  const payouts = [];

  const closeDate = new Date(deal.closeDate);
  const goLiveDate = new Date(deal.goLiveDate);

  const isMonthly =
    deal.billingType === "Monthly - Billed on Go-Live";

  const isQuarterly =
    deal.billingType === "Quarterly - Billed on Go-Live";

  if (!isMonthly && !isQuarterly) {
    return [];
  }

  // advance
  const advanceAmount =
    financials.arrCommission * 0.25;

  const advanceDate =
    moveToMondayIfWeekend(
      getNextMonthDay(closeDate, 10)
    );

  payouts.push({
    dealId: deal.dealId,
    dealOwner: deal.dealOwner,
    component: "Advance",
    payoutDate: advanceDate,
    amount: advanceAmount
  });

  // commission per invoice
  const invoiceAmount = isMonthly
    ? financials.arr / 12
    : financials.arr / 4;

  const commissionPerInvoice =
    invoiceAmount * financials.arrCommissionRate;

  let remainingRecovery = advanceAmount;

  let invoiceDate = new Date(goLiveDate);

  const cutoffDate =
    new Date(2027, 2, 31); // 31-Mar-2027

  while (invoiceDate <= cutoffDate) {

    const collectionDate =
      addWorkingDays(
        invoiceDate,
        deal.paymentTerms
      );

    // Month following collection
    let payoutYear =
      collectionDate.getFullYear();

    let payoutMonth =
      collectionDate.getMonth() + 1;

    if (payoutMonth > 11) {
      payoutMonth = 0;
      payoutYear++;
    }

    const payoutDate =
      getLastFridayOfMonth(
        payoutYear,
        payoutMonth
      );

    // don't include payout after cutoff
    if (payoutDate > cutoffDate) {
      break;
    }

    const recovery =
      Math.min(
        remainingRecovery,
        commissionPerInvoice
      );

    const netPayout =
      commissionPerInvoice - recovery;

    payouts.push({
      dealId: deal.dealId,
      dealOwner: deal.dealOwner,
      component: isMonthly
        ? "Monthly Commission"
        : "Quarterly Commission",
      invoiceDate: new Date(invoiceDate),
      collectionDate: collectionDate,
      payoutDate: payoutDate,
      grossCommission: commissionPerInvoice,
      recoveredAdvance: recovery,
      amount: netPayout
    });

    remainingRecovery -= recovery;

    // Next invoice
    if (isMonthly) {

      invoiceDate = new Date(
        invoiceDate.getFullYear(),
        invoiceDate.getMonth() + 1,
        invoiceDate.getDate()
      );

    } else {

      invoiceDate = new Date(
        invoiceDate.getFullYear(),
        invoiceDate.getMonth() + 3,
        invoiceDate.getDate()
      );
    }
  }

  return payouts;
}


function runPayoutCalculations() {

  const spreadsheet =
    SpreadsheetApp.getActiveSpreadsheet();

  const payoutsSheet =
    spreadsheet.getSheetByName("Payouts");

  if (!payoutsSheet) {
    throw new Error("Payouts sheet does not exist.");
  }
      // get all raw deals
  const deals = getDeals();

  const headers = [
    "Deal ID",
    "Deal Owner",
    "Component",
    "Invoice Date",
    "Collection Date",
    "Payout Date",
    "Gross Commission",
    "Recovered Advance",
    "Payout Amount"
  ];

  payoutsSheet.clearContents();
  //write headers(in row 1)
  payoutsSheet
    .getRange(1, 1, 1, headers.length)
    .setValues([headers]);

  const output = [];

  deals.forEach(deal => {
    //calculate finafncials for every deal
    const financials =
      calculateFinancials(deal);

    // generate annual payouts
    const annualPayouts =
      createAnnualPayouts(
        deal,
        financials
      );

    // monthly/quarterly payouts
    const recurringPayouts =
      createRecurringPayouts(
        deal,
        financials
      );

let normalPayouts =
  annualPayouts.concat(recurringPayouts);
  //cancellation, if deal was cancelled before go-live, if yes then was any qualifying commission already paid
if (
  deal.cancellationDate &&
  new Date(deal.cancellationDate) < new Date(deal.goLiveDate)
) {
  const cancellationDate =
    new Date(deal.cancellationDate);

  normalPayouts =
    normalPayouts.filter(payout => {
      return new Date(payout.payoutDate) <= cancellationDate;
    });
}

const clawbacks =
  createCancellationClawback(
    deal,
    normalPayouts
  );
    //now combine everything
const allPayouts =
  normalPayouts.concat(clawbacks);

    allPayouts.forEach(payout => {

      output.push([
        payout.dealId,
        payout.dealOwner,
        payout.component,
        payout.invoiceDate || "",
        payout.collectionDate || "",
        payout.payoutDate,
        payout.grossCommission || "",
        payout.recoveredAdvance || "",
        payout.amount
      ]);

    });

  });

  if (output.length > 0) {

    payoutsSheet
      .getRange(
        2,
        1,
        output.length,
        headers.length
      )
      .setValues(output);

  }

  payoutsSheet.autoResizeColumns(
    1,
    headers.length
  );

  Logger.log(
    "Payout calculations completed. Total payout rows: " +
    output.length
  );
}

function createCancellationClawback(deal, existingPayouts) {

  // No cancellation
  if (!deal.cancellationDate) {
    return [];
  }

  const cancellationDate =
    new Date(deal.cancellationDate);

  const goLiveDate =
    new Date(deal.goLiveDate);

  // Clawback only applies when cancelled before go-live
  if (cancellationDate >= goLiveDate) {
    return [];
  }

  let clawbackAmount = 0;

  // find payouts that were already paid
  existingPayouts.forEach(payout => {

    const payoutDate =
      new Date(payout.payoutDate);

    // only payouts paid on or before cancellation
    if (payoutDate <= cancellationDate) {

      if (
        payout.component === "Advance" ||
        payout.component === "Implementation" ||
        payout.component === "Implementation - Signing"
      ) {
        clawbackAmount += payout.amount;
      }
    }
  });

  if (clawbackAmount === 0) {
    return [];
  }

  // Clawback date = 10th of following month
  const clawbackDate =
    moveToMondayIfWeekend(
      getNextMonthDay(cancellationDate, 10)
    );

  return [{
    dealId: deal.dealId,
    dealOwner: deal.dealOwner,
    component: "Cancellation Clawback",
    payoutDate: clawbackDate,
    amount: -clawbackAmount
  }];
}

function getCurrentUser() {

  const email =
    Session.getActiveUser().getEmail();
    // if not email recieved from google then error
  if (!email) {
    throw new Error(
      "Unable to identify the logged-in Google user."
    );
  }

  const sheet =
    SpreadsheetApp
      .getActiveSpreadsheet()
      .getSheetByName("Users");

  const data =
    sheet.getDataRange().getValues();

  for (let i = 1; i < data.length; i++) {

    if (
      String(data[i][0]).toLowerCase() ===
      email.toLowerCase() &&
      data[i][4] === true
    ) {

      return {
        email: data[i][0],
        name: data[i][1],
        role: data[i][2],
        managerEmail: data[i][3]
      };
    }
  }

  throw new Error(
    "User is not authorized to access this application."
  );
}
function getAuthorizedData() {

  const user = getCurrentUser();

  const spreadsheet =
    SpreadsheetApp.getActiveSpreadsheet();

  const calculationsSheet =
    spreadsheet.getSheetByName("Calculations");

  const payoutsSheet =
    spreadsheet.getSheetByName("Payouts");

  const calculations =
    calculationsSheet
      .getDataRange()
      .getValues();

  const payouts =
    payoutsSheet
      .getDataRange()
      .getValues();

  // remove headers
  const calculationRows =
    calculations.slice(1);

  const payoutRows =
    payouts.slice(1);


  // ADMIN


  if (user.role === "Admin") {

    return {
      user: user,
      calculations: calculationRows,
      payouts: payoutRows
    };
  }

  // MANAGER

  if (user.role === "Manager") {

    const usersSheet =
      spreadsheet.getSheetByName("Users");

    const users =
      usersSheet
        .getDataRange()
        .getValues()
        .slice(1);

    const teamEmails = users
      .filter(row =>
        row[3] === user.email &&
        row[4] === true
      )
      .map(row =>
        String(row[0]).toLowerCase()
      );

    const teamNames = users
      .filter(row =>
        row[3] === user.email &&
        row[4] === true
      )
      .map(row =>
        String(row[1]).toLowerCase()
      );
      // shows filteres calc only belonging to manager's team
    const filteredCalculations =
      calculationRows.filter(row =>
        teamNames.includes(
          String(row[3]).toLowerCase()
        )
      );

    const filteredPayouts =
      payoutRows.filter(row =>
        teamNames.includes(
          String(row[1]).toLowerCase()
        )
      );

    return {
      user: user,
      calculations: filteredCalculations,
      payouts: filteredPayouts
    };
  }

  // AE

  if (user.role === "AE") {

    const filteredCalculations =
      calculationRows.filter(row =>
        String(row[3]).toLowerCase() ===
        user.name.toLowerCase()
      );

    const filteredPayouts =
      payoutRows.filter(row =>
        String(row[1]).toLowerCase() ===
        user.name.toLowerCase()
      );

    return {
      user: user,
      calculations: filteredCalculations,
      payouts: filteredPayouts
    };
  }

  throw new Error("Invalid user role.");
}

function doGet() {
  return HtmlService
    .createHtmlOutputFromFile("Index")
    .setTitle("Lumberfi Commission Dashboard");
}
function getDashboardData() {

  const data = getAuthorizedData();

  // convert Date objects into strings
  // so they can safely be sent to the HTML frontend.
  return JSON.parse(
    JSON.stringify(data)
  );
}
function adminRecalculate() {

  const user = getCurrentUser();

  if (user.role !== "Admin") {
    throw new Error(
      "Access denied. Admin privileges are required."
    );
  }

  runFinancialCalculations();
  runPayoutCalculations();

  return {
    success: true,
    message: "Financial calculations and payouts recalculated successfully."
  };
}
function adminUploadDeals(csvContent) {

  const user = getCurrentUser();

  if (user.role !== "Admin") {
    throw new Error(
      "Access denied. Admin privileges are required."
    );
  }

  if (!csvContent) {
    throw new Error("No CSV file was provided.");
  }

  const spreadsheet =
    SpreadsheetApp.getActiveSpreadsheet();

  const dealsSheet =
    spreadsheet.getSheetByName("Deals");

  if (!dealsSheet) {
    throw new Error("Deals sheet does not exist.");
  }

  const rows =
    Utilities.parseCsv(csvContent);
  const normalizedRows = normalizeDealRows(rows);

  if (normalizedRows.length < 2) {
    throw new Error(
      "CSV does not contain any deal records."
    );
  }

  // Replace existing deal data
  dealsSheet.clearContents();

  dealsSheet
    .getRange(
      1,
      1,
      normalizedRows.length,
      normalizedRows[0].length
    )
    .setValues(normalizedRows);

  // Recalculate everything
  runFinancialCalculations();
  runPayoutCalculations();

  return {
    success: true,
    message:
      "Deal dump uploaded and commissions recalculated successfully.",
    dealCount: rows.length - 1
  };
}
function normalizeDealRows(rows) {

  return rows.map((row, index) => {

    // Header
    if (index === 0) {
      return row;
    }

    // Remove accidental trailing empty columns
    while (
      row.length > 17 &&
      row[row.length - 1] === ""
    ) {
      row.pop();
    }

    // Handle unquoted TCV containing comma
    if (
      row.length > 17 &&
      typeof row[11] === "string" &&
      row[11].includes("$") &&
      !isNaN(Number(row[12]))
    ) {

      row[11] =
        row[11] + "," + row[12];

      row.splice(12, 1);
    }

    // Handle unquoted Implementation Fee containing comma
    if (
      row.length > 17 &&
      typeof row[12] === "string" &&
      row[12].includes("$") &&
      !isNaN(Number(row[13]))
    ) {

      row[12] =
        row[12] + "," + row[13];

      row.splice(13, 1);
    }

    // TCV
    row[11] =
      parseMoneyValue(row[11]);

    // Implementation Fee
    row[12] =
      parseMoneyValue(row[12]);

    // Payment Terms
    if (
      row[16] === "-" ||
      row[16] === "" ||
      row[16] === null
    ) {
      row[16] = 0;
    }

    return row;

  });

}
function parseMoneyValue(value) {

  if (
    value === null ||
    value === undefined ||
    value === "" ||
    String(value).trim() === "-"
  ) {
    return 0;
  }

  if (typeof value === "number") {
    return value;
  }

  const cleaned =
    String(value)
      .replace("$", "")
      .replace(/,/g, "")
      .trim();

  const number =
    Number(cleaned);

  if (isNaN(number)) {
    throw new Error(
      "Invalid monetary value: " + value
    );
  }

  return number;
}
