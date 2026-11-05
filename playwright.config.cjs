module.exports = {
  testDir: './tests', testMatch: '**/membership-browser.cjs',
  use: { headless:true, launchOptions: process.env.DD_TEST_CHROME ? {executablePath:process.env.DD_TEST_CHROME} : {} },
  reporter: 'list'
};
