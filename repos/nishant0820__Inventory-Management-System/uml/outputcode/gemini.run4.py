import tkinter as tk
from tkinter import ttk
from typing import Optional, Union, Any, List

class categoryClass:
    def __init__(self, root: Union[tk.Tk, tk.Toplevel]):
        self.root = root
        self.var_cat_id = tk.StringVar()
        self.var_name = tk.StringVar()
        self.im1: Optional[tk.PhotoImage] = None
        self.im2: Optional[tk.PhotoImage] = None
        self.lbl_im1 = tk.Label(self.root)
        self.lbl_im2 = tk.Label(self.root)
        self.CategoryTable = ttk.Treeview(self.root)

    def add(self) -> None:
        pass

    def clear(self) -> None:
        pass

    def delete(self) -> None:
        pass

    def get_data(self, ev: Any) -> None:
        pass

    def show(self) -> None:
        pass


class employeeClass:
    def __init__(self, root: Union[tk.Tk, tk.Toplevel]):
        self.root = root
        self.var_searchby = tk.StringVar()
        self.var_searchtxt = tk.StringVar()
        self.var_emp_id = tk.StringVar()
        self.var_gender = tk.StringVar()
        self.var_contact = tk.StringVar()
        self.var_name = tk.StringVar()
        self.var_dob = tk.StringVar()
        self.var_doj = tk.StringVar()
        self.var_email = tk.StringVar()
        self.var_pass = tk.StringVar()
        self.var_utype = tk.StringVar()
        self.var_salary = tk.StringVar()
        self.txt_address = tk.Text(self.root)
        self.EmployeeTable = ttk.Treeview(self.root)

    def add(self) -> None:
        pass

    def clear(self) -> None:
        pass

    def delete(self) -> None:
        pass

    def get_data(self, ev: Any) -> None:
        pass

    def search(self) -> None:
        pass

    def show(self) -> None:
        pass

    def update(self) -> None:
        pass


class productClass:
    def __init__(self, root: Union[tk.Tk, tk.Toplevel]):
        self.root = root
        self.var_searchby = tk.StringVar()
        self.var_searchtxt = tk.StringVar()
        self.var_pid = tk.StringVar()
        self.var_cat = tk.StringVar()
        self.var_sup = tk.StringVar()
        self.var_name = tk.StringVar()
        self.var_price = tk.StringVar()
        self.var_qty = tk.StringVar()
        self.var_status = tk.StringVar()
        self.cat_list: List[Any] = []
        self.sup_list: List[Any] = []
        self.ProductTable = ttk.Treeview(self.root)

    def add(self) -> None:
        pass

    def clear(self) -> None:
        pass

    def delete(self) -> None:
        pass

    def fetch_cat_sup(self) -> None:
        pass

    def get_data(self, ev: Any) -> None:
        pass

    def search(self) -> None:
        pass

    def show(self) -> None:
        pass

    def update(self) -> None:
        pass


class salesClass:
    def __init__(self, root: Union[tk.Tk, tk.Toplevel]):
        self.root = root
        self.var_invoice = tk.StringVar()
        self.bill_photo: Optional[tk.PhotoImage] = None
        self.blll_list: List[Any] = []
        self.Sales_List = tk.Listbox(self.root)
        self.bill_area = tk.Text(self.root)

    def clear(self) -> None:
        pass

    def get_data(self, ev: Any) -> None:
        pass

    def search(self) -> None:
        pass

    def show(self) -> None:
        pass


class supplierClass:
    def __init__(self, root: Union[tk.Tk, tk.Toplevel]):
        self.root = root
        self.var_searchby = tk.StringVar()
        self.var_searchtxt = tk.StringVar()
        self.var_sup_invoice = tk.StringVar()
        self.var_name = tk.StringVar()
        self.var_contact = tk.StringVar()
        self.txt_desc = tk.Text(self.root)
        self.SupplierTable = ttk.Treeview(self.root)

    def add(self) -> None:
        pass

    def clear(self) -> None:
        pass

    def delete(self) -> None:
        pass

    def get_data(self, ev: Any) -> None:
        pass

    def search(self) -> None:
        pass

    def show(self) -> None:
        pass

    def update(self) -> None:
        pass


class billClass:
    def __init__(self, root: Union[tk.Tk, tk.Toplevel]):
        self.root = root
        self.var_search = tk.StringVar()
        self.var_cname = tk.StringVar()
        self.var_contact = tk.StringVar()
        self.var_cal_input = tk.StringVar()
        self.var_pid = tk.StringVar()
        self.var_pname = tk.StringVar()
        self.var_price = tk.StringVar()
        self.var_qty = tk.StringVar()
        self.var_stock = tk.StringVar()
        
        self.cart_list: List[Any] = []
        self.chk_print: int = 0
        self.bill_amnt: int = 0
        self.discount: float = 0.0
        self.net_pay: Union[float, int] = 0.0
        self.siscount: int = 0
        self.invoice: Any = None
        
        self.icon_title: Optional[tk.PhotoImage] = None
        
        self.lbl_clock = tk.Label(self.root)
        self.lbl_amnt = tk.Label(self.root)
        self.lbl_discount = tk.Label(self.root)
        self.lbl_net_pay = tk.Label(self.root)
        self.lbl_inStock = tk.Label(self.root)
        self.cartTitle = tk.Label(self.root)
        
        self.txt_cal_input = tk.Entry(self.root)
        self.txt_bill_area = tk.Text(self.root)
        
        self.product_Table = ttk.Treeview(self.root)
        self.CartTable = ttk.Treeview(self.root)

    def add_update_cart(self) -> None:
        pass

    def bill_bottom(self) -> None:
        pass

    def bill_middle(self) -> None:
        pass

    def bill_top(self) -> None:
        pass

    def bill_update(self) -> None:
        pass

    def clear_all(self) -> None:
        pass

    def clear_cal(self) -> None:
        pass

    def clear_cart(self) -> None:
        pass

    def generate_bill(self) -> None:
        pass

    def get_data(self, ev: Any) -> None:
        pass

    def get_data_cart(self, ev: Any) -> None:
        pass

    def get_input(self, num: Any) -> None:
        pass

    def perform_cal(self) -> None:
        pass

    def print_bill(self) -> None:
        pass

    def search(self) -> None:
        pass

    def show(self) -> None:
        pass

    def show_cart(self) -> None:
        pass

    def update_date_time(self) -> None:
        pass


class IMS:
    def __init__(self, root: Union[tk.Tk, tk.Toplevel]):
        self.root = root
        self.new_win: Optional[tk.Toplevel] = None
        self.new_obj: Any = None
        
        self.MenuLogo: Optional[tk.PhotoImage] = None
        self.icon_side: Optional[tk.PhotoImage] = None
        self.icon_title: Optional[tk.PhotoImage] = None
        
        self.lbl_clock = tk.Label(self.root)
        self.lbl_category = tk.Label(self.root)
        self.lbl_employee = tk.Label(self.root)
        self.lbl_product = tk.Label(self.root)
        self.lbl_sales = tk.Label(self.root)
        self.lbl_supplier = tk.Label(self.root)

    def category(self) -> None:
        self.new_win = tk.Toplevel(self.root)
        self.new_obj = categoryClass(self.new_win)

    def employee(self) -> None:
        self.new_win = tk.Toplevel(self.root)
        self.new_obj = employeeClass(self.new_win)

    def product(self) -> None:
        self.new_win = tk.Toplevel(self.root)
        self.new_obj = productClass(self.new_win)

    def sales(self) -> None:
        self.new_win = tk.Toplevel(self.root)
        self.new_obj = salesClass(self.new_win)

    def supplier(self) -> None:
        self.new_win = tk.Toplevel(self.root)
        self.new_obj = supplierClass(self.new_win)

    def update_content(self) -> None:
        pass

if __name__ == "__main__":
    root = tk.Tk()
    app = IMS(root)
    root.mainloop()