from .obsiquery_app import ObsiQueryBot


bot = ObsiQueryBot()

def test_run():
    response = bot.invoke_graph("can please check what is the problem statement in the obsiquery - prd ? ","2")
    # print(response)