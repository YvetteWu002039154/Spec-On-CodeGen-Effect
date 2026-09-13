import tkinter as tk
from tkinter import ttk
from typing import Optional, List, Union, Any

class categoryClass:
    def __init__(self, root: Union[tk.Tk, tk.Toplevel]) -> None:
        self.root: Union[tk.Tk, tk.Toplevel] = root
        self.im1: Optional[tk.PhotoImage] = None
        self.im2: Optional[tk.PhotoImage] = None
        self.lbl_im1: Optional[tk.Label] = None
        self.lbl_im2: Optional[tk.Label] = None
        self.var_cat_id: tk.StringVar = tk.StringVar()
        self.var_name: tk.StringVar = tk.StringVar()
        self.CategoryTable: Optional[ttk.Treeview] = None

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
    def __init__(self, root: Union[tk.Tk, tk.Toplevel]) -> None:
        self.root: Union[tk.Tk, tk.Toplevel] = root
        self.txt_address: Optional[tk.Text] = None
        self.var_contact: tk.StringVar = tk.StringVar()
        self.var_dob: tk.StringVar = tk.StringVar()
        self.var_doj: tk.StringVar = tk.StringVar()
        self.var_email: tk.StringVar = tk.StringVar()
        self.var_emp_id: tk.StringVar = tk.StringVar()
        self.var_gender: tk.StringVar = tk.StringVar()
        self.var_name: tk.StringVar = tk.StringVar()
        self.var_pass: tk.StringVar = tk.StringVar()
        self.var_salary: tk.StringVar = tk.StringVar()
        self.var_searchby: tk.StringVar = tk.StringVar()
        self.var_searchtxt: tk.StringVar = tk.StringVar()
        self.var_utype: tk.StringVar = tk.StringVar()
        self.EmployeeTable: Optional[ttk.Treeview] = None

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
    def __init__(self, root: Union[tk.Tk, tk.Toplevel]) -> None:
        self.root: Union[tk.Tk, tk.Toplevel] = root
        self.cat_list: List[Any] = []
        self.sup_list: List[Any] = []
        self.var_cat: tk.StringVar = tk.StringVar()
        self.var_name: tk.StringVar = tk.StringVar()
        self.var_pid: tk.StringVar = tk.StringVar()
        self.var_price: tk.StringVar = tk.StringVar()
        self.var_qty: tk.StringVar = tk.StringVar()
        self.var_searchby: tk.StringVar = tk.StringVar()
        self.var_searchtxt: tk.StringVar = tk.StringVar()
        self.var_status: tk.StringVar = tk.StringVar()
        self.var_sup: tk.StringVar = tk.StringVar()
        self.ProductTable: Optional[ttk.Treeview] = None

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
    def __init__(self, root: Union[tk.Tk, tk.Toplevel]) -> None:
        self.root: Union[tk.Tk, tk.Toplevel] = root
        self.bill_area: Optional[tk.Text] = None
        self.bill_photo: Optional[tk.PhotoImage] = None
        self.blll_list: List[Any] = []
        self.var_invoice: tk.StringVar = tk.StringVar()
        self.Sales_List: Optional[tk.Listbox] = None

    def clear(self) -> None:
        pass

    def get_data(self, ev: Any) -> None:
        pass

    def search(self) -> None:
        pass

    def show(self) -> None:
        pass


class supplierClass:
    def __init__(self, root: Union[tk.Tk, tk.Toplevel]) -> None:
        self.root: Union[tk.Tk, tk.Toplevel] = root
        self.txt_desc: Optional[tk.Text] = None
        self.var_contact: tk.StringVar = tk.StringVar()
        self.var_name: tk.StringVar = tk.StringVar()
        self.var_searchby: tk.StringVar = tk.StringVar()
        self.var_searchtxt: tk.StringVar = tk.StringVar()
        self.var_sup_invoice: tk.StringVar = tk.StringVar()
        self.SupplierTable: Optional[ttk.Treeview] = None

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
    def __init__(self, root: Union[tk.Tk, tk.Toplevel]) -> None:
        self.root: Union[tk.Tk, tk.Toplevel] = root
        self.bill_amnt: int = 0
        self.cart_list: List[Any] = []
        self.chk_print: int = 0
        self.discount: float = 0.0
        self.icon_title: Optional[tk.PhotoImage] = None
        self.invoice: Any = None
        self.net_pay: Union[float, int] = 0.0
        self.siscount: int = 0
        self.var_cal_input: tk.StringVar = tk.StringVar()
        self.var_cname: tk.StringVar = tk.StringVar()
        self.var_contact: tk.StringVar = tk.StringVar()
        self.var_pid: tk.StringVar = tk.StringVar()
        self.var_pname: tk.StringVar = tk.StringVar()
        self.var_price: tk.StringVar = tk.StringVar()
        self.var_qty: tk.StringVar = tk.StringVar()
        self.var_search: tk.StringVar = tk.StringVar()
        self.var_stock: tk.StringVar = tk.StringVar()
        
        self.CartTable: Optional[ttk.Treeview] = None
        self.cartTitle: Optional[tk.Label] = None
        self.lbl_amnt: Optional[tk.Label] = None
        self.lbl_clock: Optional[tk.Label] = None
        self.lbl_discount: Optional[tk.Label] = None
        self.lbl_inStock: Optional[tk.Label] = None
        self.lbl_net_pay: Optional[tk.Label] = None
        self.product_Table: Optional[ttk.Treeview] = None
        self.txt_bill_area: Optional[tk.Text] = None
        self.txt_cal_input: Optional[tk.Entry] = None

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
    def __init__(self, root: Union[tk.Tk, tk.Toplevel]) -> None:
        self.root: Union[tk.Tk, tk.Toplevel] = root
        self.MenuLogo: Optional[tk.PhotoImage] = None
        self.icon_side: Optional[tk.PhotoImage] = None
        self.icon_title: Optional[tk.PhotoImage] = None
        self.lbl_category: Optional[tk.Label] = None
        self.lbl_clock: Optional[tk.Label] = None
        self.lbl_employee: Optional[tk.Label] = None
        self.lbl_product: Optional[tk.Label] = None
        self.lbl_sales: Optional[tk.Label] = None
        self.lbl_supplier: Optional[tk.Label] = None
        self.new_obj: Any = None
        self.new_win: Optional[tk.Toplevel] = None

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