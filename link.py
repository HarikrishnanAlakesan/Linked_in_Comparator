import streamlit as st
import os
import time
import pickle
import google.generativeai as genai
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from fpdf import FPDF

# --- Configuration ---
USERNAME = "mailhkris@gmail.com"
PASSWORD = "04hari2004"
MY_PROFILE_URL = "https://www.linkedin.com/in/harikrishnan-alakesan-05a442215/"
COOKIE_FILE = "linkedin_cookies.pkl"
genai.configure(api_key="AIzaSyCagnPGqPk2pPzyvkaA6DYxt1ReIVN2tOE")  # Replace with your actual API key

# --- Helper Functions ---
def init_driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new")  # run in headless mode
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    return webdriver.Chrome(options=options)

def save_cookies(driver):
    with open(COOKIE_FILE, "wb") as f:
        pickle.dump(driver.get_cookies(), f)

def load_cookies(driver):
    if os.path.exists(COOKIE_FILE):
        with open(COOKIE_FILE, "rb") as f:
            cookies = pickle.load(f)
            for cookie in cookies:
                driver.add_cookie(cookie)
        return True
    return False

def login(driver):
    driver.get("https://www.linkedin.com/login")
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "username")))
    driver.find_element(By.ID, "username").send_keys(USERNAME)
    driver.find_element(By.ID, "password").send_keys(PASSWORD)
    driver.find_element(By.ID, "password").submit()
    time.sleep(5)
    save_cookies(driver)

def ensure_logged_in(driver):
    driver.get("https://www.linkedin.com")
    if not load_cookies(driver):
        login(driver)
    driver.get("https://www.linkedin.com/feed/")

def scrape_profile(driver, url):
    driver.get("https://www.linkedin.com/feed/")
    time.sleep(3)
    driver.get(url)
    time.sleep(5)
    return driver.find_element(By.TAG_NAME, "body").text

def compare_profiles(my_text, other_text):
    prompt = f"""
You are a career advisor AI. Compare the two LinkedIn profiles based on:
- Experience: Focus on the depth, relevance, and impact of their roles.
- Skills: Analyze the listed skills and their endorsement levels.
- Achievements: Identify quantifiable accomplishments and their significance.
- Clarity: Assess the overall organization, conciseness, and professional tone of the profile.

Profile 1 (Your Profile):
{my_text}

Profile 2 (Competitor Profile):
{other_text}

Provide a detailed comparison highlighting the strengths and weaknesses of each profile in the mentioned categories. Conclude with specific, actionable recommendations on how Profile 1 can be improved based on the comparison with Profile 2. Structure your response clearly with headings for each category and a final 'Recommendations for Improvement' section.
"""
    model = genai.GenerativeModel("gemini-1.5-flash")
    response = model.generate_content(prompt)
    return response.text.strip()

def generate_pdf_report_fpdf(comparison_results):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, "LinkedIn Profile Comparison Report", 0, 1, 'C')
    pdf.ln(10)
    pdf.set_font("Arial", '', 12)

    for i, (url, result) in enumerate(comparison_results.items()):
        pdf.set_font("Arial", 'B', 14)
        pdf.cell(0, 10, f"Comparison with Profile {i+1}: {url}", 0, 1)
        pdf.ln(5)
        pdf.set_font("Arial", '', 12)
        # Splitting the text into lines to fit within the page width
        line_height = 6
        page_width = 210 - 20  # A4 page width minus margins
        text = result.encode('latin-1', 'ignore').decode('latin-1') # Handle potential encoding issues

        for line in text.splitlines():
            while pdf.get_string_width(line) > page_width:
                split_index = -1
                for j in range(len(line)):
                    if pdf.get_string_width(line[:j+1]) > page_width:
                        split_index = j
                        break
                if split_index == -1:
                    break
                pdf.cell(0, line_height, line[:split_index], 0, 1)
                line = line[split_index:]
            pdf.cell(0, line_height, line, 0, 1)
        pdf.ln(10)

    pdf.output("linkedin_comparison_report_fpdf.pdf", "F")
    st.success("✅ Comparison report generated as linkedin_comparison_report_fpdf.pdf")

# --- Streamlit UI ---
st.set_page_config(page_title="LinkedIn Profile Comparator", layout="wide")
st.title("🔍 LinkedIn Profile Comparator with Gemini AI")

st.markdown("""
This tool compares your LinkedIn profile against others using **Google Gemini AI**.
Paste the LinkedIn URLs you want to compare below (one per line).
""")

profile_urls_input = st.text_area("📎 Paste LinkedIn Profile URLs (one per line)", height=200)
compare_button = st.button("Compare Now")

if compare_button and profile_urls_input.strip():
    profile_urls = [url.strip() for url in profile_urls_input.splitlines() if url.strip()]
    comparison_results = {}

    with st.spinner("Starting comparison..."):
        driver = init_driver()
        ensure_logged_in(driver)

        st.subheader("👤 Your Profile")
        my_text = scrape_profile(driver, MY_PROFILE_URL)
        st.success("✅ Scraped your profile successfully.")

        for idx, url in enumerate(profile_urls, start=1):
            try:
                st.markdown(f"---\n### 🔗 Competitor Profile #{idx}")
                other_text = scrape_profile(driver, url)
                st.success(f"✅ Scraped profile #{idx}")

                st.markdown("💡 **Gemini's Comparison Result:**")
                result = compare_profiles(my_text, other_text)
                st.info(result)
                comparison_results[url] = result
            except Exception as e:
                st.error(f"❌ Failed to compare with {url}: {e}")

        driver.quit()

    if comparison_results:
        generate_pdf_report_fpdf(comparison_results)
