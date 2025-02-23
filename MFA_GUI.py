import tkinter as tk
import time

i = 123456

def counter(i):
#   greeting.config(text = str(i),fg="red", bg="yellow")
    greeting = tk.Label(text=str(i),
                    width=codeFrame_width,
                    height=codeFrame_height,
                    relief=tk.RAISED,
                    borderwidth=1
    )                    

def dun():

    quit()


#########################

window = tk.Tk()

#
#window.attributes('-fullscreen', True)
#window.overrideredirect(False)
window.title("3D MFA Test")

window_width= window.winfo_screenwidth()               
window_height= window.winfo_screenheight()               
window.geometry("%dx%d" % (window_width, window_height))

#window.resizable(False, False)

codeFrame_width = 15
codeFrame_height = 1

greeting = tk.Label(text=str(i),
                    width=codeFrame_width,
                    height=codeFrame_height,
                    relief=tk.RAISED,
                    borderwidth=1
)
greeting.config(font=("TkDefaultFont", 333))

text=("codeFrame_width: "+str(codeFrame_width)+" codeFrame_height: "+str(codeFrame_height)+"\n"+
    " window_width: " + str(window_width), " window_height: "+str(window_height)
      )



my_button = tk.Button(window,
                   text = "Please update",
                   command = counter(i)
                   )
incr_button = tk.Button(window,
                   text = "Increment",
                   command = lambda: i+1
                   )
                   
quit_button = tk.Button(window,
                   text = "Quit",
                   command = dun
                   )
#time.sleep(2)
#greeting = tk.Label(text="RED ALERT",fg="red", bg="yellow")

greeting.pack()
my_button.pack()
incr_button.pack()
quit_button.pack()

print (i,"/n")

window.mainloop()
