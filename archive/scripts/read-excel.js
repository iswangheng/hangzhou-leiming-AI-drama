const XLSX = require('xlsx');
const filePath = process.argv[2];

console.log(`读取文件: ${filePath}`);
const workbook = XLSX.readFile(filePath);
const sheetName = workbook.SheetNames[0];
const worksheet = workbook.Sheets[sheetName];
const data = XLSX.utils.sheet_to_json(worksheet);

console.log('\n=== 表头 ===');
const headers = Object.keys(data[0] || {});
console.log(headers.join(', '));

console.log('\n=== 前5行数据 ===');
data.slice(0, 5).forEach((row, i) => {
  console.log(`\n行 ${i + 1}:`);
  Object.entries(row).forEach(([key, value]) => {
    console.log(`  ${key}: ${value}`);
  });
});

console.log(`\n总行数: ${data.length}`);
