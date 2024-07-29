from django.urls import path
from . import views
from .views import (
    JobFileListView,
    ModuleFileListView,
    JSONToMXLView,
    XMLToJSONView,
    FileUploadView,
    AddNewFileView,
    DelJobView,
    RunJobView
)

urlpatterns = [
    path("geodiskin/", views.GeoDiskInListCreateView.as_view(), name="geodiskin"),
    path("job-files/", JobFileListView.as_view(), name="job_file_list"),
    path("module-files/", ModuleFileListView.as_view(), name="module_file_list"),
    path("add-new-file/", AddNewFileView.as_view(), name="add-new-file"),
    path("xml-to-json/", XMLToJSONView.as_view(), name="xml-to-json"),
    path('upload-file/', FileUploadView.as_view(), name='upload-file'),
    path("json-to-xml/", JSONToMXLView.as_view(), name="json-to-xml"),
    path("delete-job/", DelJobView.as_view(), name="delete-job"),
    path('run-job/', RunJobView.as_view(), name='run-job'),
]
