from action_handler import ActionHandler

def test_parse_response():
    handler = ActionHandler()
    
    # Case 1: /kick 1
    html1 = """
    <html>
    <body>
    <form>
    <textarea name="out" rows="10" readonly>
    Player topias is kicked out for 5 minutes! (by WEB-admin)
    </textarea>
    </form>
    </body>
    </html>
    """
    
    # Case 2: /unban 0
    html2 = """
    <html>
    <body>
    <form>
    <textarea name="out" rows="10" readonly>
    Banned address (topias) set back to OK. (by WEB-admin)
    </textarea>
    </form>
    </body>
    </html>
    """
    
    # Case 3: /unban (list)
    html3 = """
    <html>
    <body>
    <form>
    <textarea name="out" rows="10" readonly>
    Select address to unban or ALL to unban all.
    Banned addresses:
    [0] topias [162.159.134.234] (9999990 min left)
    </textarea>
    </form>
    </body>
    </html>
    """
    
    # Case 4: Pure text response
    text4 = "Simple success message"
    
    # Case 5: HTML entities
    html5 = """
    <textarea>&lt;b&gt;Player&lt;/b&gt; kicked &amp; banned.</textarea>
    """

    print("Testing Case 1 (kick):")
    res1 = handler._parse_admin_response(html1)
    print(f"Result: '{res1}'")
    
    print("\nTesting Case 2 (unban):")
    res2 = handler._parse_admin_response(html2)
    print(f"Result: '{res2}'")
    
    print("\nTesting Case 3 (list):")
    res3 = handler._parse_admin_response(html3)
    print(f"Result: '{res3}'")

    print("\nTesting Case 4 (pure text):")
    res4 = handler._parse_admin_response(text4)
    print(f"Result: '{res4}'")

    print("\nTesting Case 5 (entities):")
    res5 = handler._parse_admin_response(html5)
    print(f"Result: '{res5}'")

if __name__ == "__main__":
    test_parse_response()
