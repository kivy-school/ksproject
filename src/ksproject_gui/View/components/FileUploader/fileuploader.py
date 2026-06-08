import os

from carbonkivy.uix.boxlayout import CBoxLayout
from carbonkivy.uix.fileuploader import CFileUploader
from kivy.properties import StringProperty


class FileUploader(CFileUploader, CBoxLayout):
    description = StringProperty()

    data_source = StringProperty(None, allownone=True)

    def __init__(self, **kwargs) -> None:
        super(FileUploader, self).__init__(**kwargs)
        self.path = "None"
        self.filters = {"Images only": ["*.jpg", "*.jpeg", "*.png"]}

    def file_select(self):
        self.upload_file()

    #     filechooser.open_file(
    #         on_selection=self.selected,
    #         title="Select an Image",
    #         filters=["*.jpeg;*.png;*.jpg"],
    #     )  # filters=[("Images only", "*.jpeg;*.jpg;*.png;")])

    # def selected(self, selection: object):
    #     try:
    #         if selection != None:
    #             print(selection[0])
    #             self.path = selection[0]
    #             self.description = self.path
    #             self.data_source = selection[0]
    #     except Exception as e:
    #         print(f"Error selecting file: {e}")

    def on_file(self, instance: object, value: str, *args) -> None:
        if self.file:
            self.description = os.path.basename(value)
            self.data_source = value
            self.path = value
