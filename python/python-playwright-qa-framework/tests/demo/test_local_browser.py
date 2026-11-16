from playwright.sync_api import expect

from src.utils.custom_commands import CustomCommands


def test_fill_and_click_on_local_form(page, context):
    page.set_content("""<label>Name <input placeholder="Name"></label>
        <button
        onclick="document.querySelector('output').textContent=document.querySelector('input').value">Save</button>
        <output></output>""")
    commands = CustomCommands(page, context)
    commands.custom_fill("input", "Synthetic contact")
    commands.custom_click("button")
    expect(page.locator("output")).to_have_text("Synthetic contact")


def test_secret_fill_masks_log(page, context, caplog):
    page.set_content('<input type="password" placeholder="Password">')
    commands = CustomCommands(page, context)
    with caplog.at_level("INFO"):
        commands.custom_fill("input", "demo-secret-value", logs=False)
    expect(page.locator("input")).to_have_value("demo-secret-value")
    assert "demo-secret-value" not in caplog.text
    assert "*********" in caplog.text
