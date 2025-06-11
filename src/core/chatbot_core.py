from .obsiquery_app import ObsiQueryBot

bot = ObsiQueryBot()

def test_run():
    response = bot.invoke_graph("hi ","2")
    print(response['reply'])
