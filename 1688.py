from playwright.sync_api import sync_playwright


# proxy = {

#     "server": 
# }
def login_and_save_session():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()

        # Go to login page
        page.goto("https://login.1688.com")
        print("Please log in manually in the browser window...")

        # Wait for user to log in
        input("Press Enter after you have logged in...")

        # Save session state
        context.storage_state(path="cookies.json")
        print("Session saved!")

        browser.close()

def fetch_orders():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        
        # Reuse session
        context = browser.new_context(storage_state="cookies.json")
        page = context.new_page()

        # Go to orders page
        page.goto(
            "https://work.1688.com/?spm=a262jm.22620049.quickentry.dbuylist.5e2e4aadKuNatl&_path_=buyer2017Base/2017sellerbase_xunjia/buyList"
        )

        # Wait a few seconds in case page elements take time to render
        page.wait_for_timeout(3000)

        # Hide popover forcibly using JS
        page.evaluate("""
            const pop = document.querySelector('#driver-popover-description');
            if(pop) { pop.style.display = 'none'; }
            const btn = document.querySelector('button.driver-popover-close-btn');
            if(btn) { btn.style.display = 'none'; }
        """)
        print("Popover forcibly hidden!")

        # Wait for orders to load
        page.wait_for_selector("span.order-id a.order-id-action")  

        # Extract order info
        order_elements = page.query_selector_all("span.order-id a.order-id-action")
        order_ids = [el.inner_text().strip() for el in order_elements]

        print("Order IDs on this page:", order_ids)

        browser.close()

if __name__ == "__main__":
    #login_and_save_session()  # Run this once to save your session
    fetch_orders()            # Fetch orders using saved session
