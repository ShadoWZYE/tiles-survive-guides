const fs=require('fs'),path=require('path');
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'C:/Users/Shadow/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
(async()=>{const browser=await chromium.launch({headless:true,executablePath:process.env.EDGE_BINARY||'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe'});
try{const page=await browser.newPage({viewport:{width:960,height:1200},deviceScaleFactor:1});
for(const lang of ['EN','RU']){const folder=path.resolve(__dirname,'../outputs/state-map/game-chat',lang);for(const name of fs.readdirSync(folder).filter(n=>n.endsWith('.svg'))){await page.setContent('<html><style>body{margin:0}</style>'+fs.readFileSync(path.join(folder,name),'utf8')+'</html>');await page.screenshot({path:path.join(folder,name.replace('.svg','.png'))});}}
console.log('Rendered 14 game-chat cards (960 x 1200).');}finally{await browser.close();}})().catch(e=>{console.error(e);process.exitCode=1});
