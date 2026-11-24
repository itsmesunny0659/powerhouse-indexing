import asyncio
from playwright.async_api import async_playwright

async def inspect_btn():
    target = 'https://sites.google.com/view/kyafaydahaibhaikyayarrindexx/home'
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(f'https://search.google.com/test/rich-results?url={target}', timeout=30000)
        await page.wait_for_timeout(3000)
        
        btn = await page.query_selector('button, div[role="button"]')
        inp = await page.query_selector('input')
        if inp:
            print('Found input! Filling target URL and pressing Enter...', flush=True)
            await inp.click()
            await inp.fill(target)
            await inp.press('Enter')
            print('Pressed Enter!', flush=True)
            
            for i in range(12):
                await page.wait_for_timeout(3000)
                body = await page.inner_text('body')
                lines = [l.strip() for l in body.split('\n') if l.strip()]
                print(f"[T+{(i+1)*3}s]:", [l for l in lines if any(k in l.lower() for k in ['test', 'url', 'crawl', 'live', 'evaluating', 'testing', 'result', 'code'])][:3], flush=True)
                if any(k in body.lower() for k in ['testing live url', 'evaluating', 'crawling']):
                    print("--> Real Googlebot WRS crawl actively running in Google Datacenter!", flush=True)
                if any(k in body.lower() for k in ['test results', 'detected items', 'no rich results']):
                    print("--> Googlebot physical crawl FINISHED!", flush=True)
                    break
                    
        await page.screenshot(path='after_enter.png')
        await browser.close()
        print('Done!', flush=True)

if __name__ == '__main__':
    asyncio.run(inspect_btn())
