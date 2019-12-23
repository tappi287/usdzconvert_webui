from app import App

if __name__ == '__main__':
    """
        This method is messy and will run App twice. Some code may gets executed twice.
        Only useful to use when IDE debugging features are needed and one would not like
        to pay for PyCharm Pro :) 
    """
    App.run()
