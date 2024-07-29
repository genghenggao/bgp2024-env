import os
from rest_framework import generics
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .serializers import GeoDiskInSerializer
from django.http import JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from .models import GeoDiskIn
import xmltodict
import json
import uuid
from django.conf import settings
import xml.etree.ElementTree as ET
from xml.dom import minidom
from django.core.files.storage import FileSystemStorage
import shutil
import re
import time

# 工作目录
folder_path = "/u1/GeoEast/ieco1.6.2/libso/batp/mod"


class GeoDiskInListCreateView(generics.ListCreateAPIView):
    queryset = GeoDiskIn.objects.all()
    serializer_class = GeoDiskInSerializer


class JobFileListView(View):
    def get(self, request):
        # 指定要查询的本地文件夹路径
        # folder_path = "/u1/GeoEast/ieco1.6.2/libso/batp/mod"
        try:
            # 获取文件夹下所有文件名
            file_names = os.listdir(folder_path)

            # 过滤出 .job 文件
            job_files = [
                file
                for file in file_names
                if file.endswith(".job")
                and os.path.isfile(os.path.join(folder_path, file))
            ]

            # Sort job_files alphabetically
            job_files.sort()

            # Transform job files into the desired format
            children = [
                {
                    "id": index + 1,
                    "label": file,
                    "role": False,
                }
                for index, file in enumerate(job_files)
            ]
            # 返回 .job 文件名列表
            return JsonResponse({"children": children})

        except Exception as e:
            # 处理异常情况
            return JsonResponse({"error": str(e)}, status=500)


class ModuleFileListView(View):
    def get(self, request):
        try:
            # Define the paths to the folders where .pdl files are located
            folder_paths = [
                "/u1/GeoEast/ieco1.6.2/libso/batp/mod/",
                "/u1/GeoEast/GeoEast4.2.2/libso/sdp/pdl/",
            ]

            # Initialize an empty list to store all .pdl files from both folders
            job_files = []

            # Iterate through each folder path
            for folder_path in folder_paths:
                # Get all file names in the folder
                file_names = os.listdir(folder_path)

                # Filter out .pdl files that are regular files
                folder_job_files = [
                    file
                    for file in file_names
                    if file.endswith(".pdl")
                    and os.path.isfile(os.path.join(folder_path, file))
                ]

                # Extend the job_files list with files from the current folder
                job_files.extend(folder_job_files)

            # Sort job_files alphabetically
            job_files.sort()

            # Transform job files into the desired format
            children = [
                {
                    "id": index + 1,
                    "label": os.path.splitext(file)[0],
                    "role": False,
                }
                for index, file in enumerate(job_files)
            ]

            # Return the list of .pdl file names sorted alphabetically
            return JsonResponse({"children": children})

        except Exception as e:
            # Handle exceptions and return an error response
            return JsonResponse({"error": str(e)}, status=500)


class AddNewFileView(APIView):
    def post(self, request):
        folder_path = request.data.get("folder_path")
        file_name = request.data.get("file_name")

        # 检查folder_path和file_name是否存在
        if not folder_path or not file_name:
            return Response(
                {"error": "folder_path and file_name are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 组合文件路径
        full_path = os.path.join(settings.MEDIA_ROOT, folder_path, file_name)

        # 检查文件是否存在
        if os.path.exists(full_path):
            return Response(
                {"error": "File already exists"}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # 确保文件夹路径存在
            os.makedirs(os.path.dirname(full_path), exist_ok=True)

            # 创建文件
            with open(full_path, "w") as file:
                file.write("")  # 写入空内容

            return Response(
                {"message": "File created successfully"}, status=status.HTTP_201_CREATED
            )

        except Exception as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# Helper function to create a node dictionary
def create_node(module, plot_item):
    node_id = str(uuid.uuid4())
    node_type = module["@name"].lower()
    properties = {}
    for param in module.get("PARAMETER", []):
        name = param["@name"].replace(" ", "_")
        value = param.get("#text", "")
        properties[name] = value
    node = {
        "id": node_id,
        "type": node_type,
        "x": int(plot_item["RECT"]["X"]),
        "y": int(plot_item["RECT"]["Y"]),
        "properties": properties,
    }
    return node



@method_decorator(csrf_exempt, name="dispatch")
class XMLToJSONView(View):
    def post(self, request):
        data = json.loads(request.body)
        folder_path = data.get("folder_path", "")
        file_name = data.get("file_name", "")
        # 获取文件路径，假设文件在静态文件夹中
        file_path = os.path.join(os.path.dirname(__file__), folder_path, file_name)

        try:
            with open(file_path, "r", encoding="utf-8") as file:
                xml_data = file.read()
                if not xml_data.strip():  # 检查文件是否为空
                    return JsonResponse({"nodes": [], "edges": []}, safe=False)

            # Parse the XML to a dictionary
            xml_dict = xmltodict.parse(xml_data)

            # 获取plot_item和module的对应关系
            plot_data = xml_dict["JOB"]["PLOT"]["POM"]
            module_data = xml_dict["JOB"]["MOUDLE"]
            jobinformation = xml_dict["JOB"]["JOBINFORMATION"]

            # 创建节点
            nodes = []
            id_to_node_map = {}
            for plot_item, module in zip(plot_data, module_data):
                node = create_node(module, plot_item)
                nodes.append(node)
                id_to_node_map[plot_item["@ID"]] = node
                
            # 创建连线（edges）
            edges = []
            for plot_item in plot_data:
                if "PREV" in plot_item and plot_item["PREV"] is not None:
                    prev_items = plot_item["PREV"].get("ITEM", [])
                    if isinstance(prev_items, dict):  # 如果只有一个PREV ITEM
                        prev_items = [prev_items]
                    for prev_item in prev_items:
                        source_id = prev_item["@ID"]
                        target_id = plot_item["@ID"]
                        edge_id = str(uuid.uuid4())
                        edge = {
                            "id": edge_id,
                            "type": "polyline",
                            "sourceNodeId": id_to_node_map[source_id]["id"],
                            "targetNodeId": id_to_node_map[target_id]["id"],
                            "startPoint": {
                                "x": int(id_to_node_map[source_id]["x"]),
                                "y": int(id_to_node_map[source_id]["y"]) + 20,
                            },
                            "endPoint": {
                                "x": int(id_to_node_map[target_id]["x"]),
                                "y": int(id_to_node_map[target_id]["y"]) - 20,
                            },
                            "properties": {},
                            "pointsList": [
                                {
                                    "x": int(id_to_node_map[source_id]["x"]),
                                    "y": int(id_to_node_map[source_id]["y"]) + 20,
                                },
                                {
                                    "x": int(id_to_node_map[target_id]["x"]),
                                    "y": int(id_to_node_map[target_id]["y"]) - 20,
                                },
                            ],
                        }
                        edges.append(edge)

            # 构建最终JSON结构
            output = {"nodes": nodes, "edges": edges, "jobinformation": jobinformation}

            # 打印或保存结果
            output_json = json.dumps(output, indent=4)
            # Return JSON response
            return JsonResponse(json.loads(output_json), safe=False)
        except FileNotFoundError:
            return JsonResponse({"error": "File not found"}, status=404)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)


class FileUploadView(View):
    def post(self, request):
        file = request.FILES["file"]
        if not file.name.endswith(".job"):
            return JsonResponse({"error": "File must end with .job"}, status=400)
        # Save the file
        fs = FileSystemStorage(location=os.path.join(settings.MEDIA_ROOT, "uploads"))
        file_name = fs.save(file.name, file)
        file_path = fs.path(file_name)

        try:
            with open(file_path, "r", encoding="utf-8") as file:
                xml_data = file.read()
                if not xml_data.strip():  # 检查文件是否为空
                    return JsonResponse({"nodes": [], "edges": []}, safe=False)

            # Parse the XML to a dictionary
            xml_dict = xmltodict.parse(xml_data)

            # 获取plot_item和module的对应关系
            plot_data = xml_dict["JOB"]["PLOT"]["POM"]
            module_data = xml_dict["JOB"]["MOUDLE"]

            # 创建节点
            nodes = []
            id_to_node_map = {}
            for plot_item, module in zip(plot_data, module_data):
                node = create_node(module, plot_item)
                nodes.append(node)
                id_to_node_map[plot_item["@ID"]] = node

            # 创建连线（edges）
            edges = []
            for plot_item in plot_data:
                if "PREV" in plot_item and plot_item["PREV"] is not None:
                    prev_items = plot_item["PREV"].get("ITEM", [])
                    if isinstance(prev_items, dict):  # 如果只有一个PREV ITEM
                        prev_items = [prev_items]
                    for prev_item in prev_items:
                        source_id = prev_item["@ID"]
                        target_id = plot_item["@ID"]
                        edge_id = str(uuid.uuid4())
                        edge = {
                            "id": edge_id,
                            "type": "polyline",
                            "sourceNodeId": id_to_node_map[source_id]["id"],
                            "targetNodeId": id_to_node_map[target_id]["id"],
                            "startPoint": {
                                "x": int(id_to_node_map[source_id]["x"]),
                                "y": int(id_to_node_map[source_id]["y"]) + 20,
                            },
                            "endPoint": {
                                "x": int(id_to_node_map[target_id]["x"]),
                                "y": int(id_to_node_map[target_id]["y"]) - 20,
                            },
                            "properties": {},
                            "pointsList": [
                                {
                                    "x": int(id_to_node_map[source_id]["x"]),
                                    "y": int(id_to_node_map[source_id]["y"]) + 20,
                                },
                                {
                                    "x": int(id_to_node_map[target_id]["x"]),
                                    "y": int(id_to_node_map[target_id]["y"]) - 20,
                                },
                            ],
                        }
                        edges.append(edge)

            # 构建最终JSON结构
            output = {"nodes": nodes, "edges": edges}

            # 打印或保存结果
            output_json = json.dumps(output, indent=4)

            return JsonResponse(json.loads(output_json), safe=False)
        except ET.ParseError:
            return JsonResponse({"error": "Failed to parse job file"}, status=400)
        finally:
            # Remove the uploaded file
            # os.remove(file_path)
            # 移动文件
            shutil.move(file_path, folder_path)


class JSONToMXLView(APIView):
    def post(self, request):
        # Extracting data from the request
        folder_path = request.data.get("folder_path", "")
        file_name = request.data.get("file_name", "")
        data_json = request.data.get("data_json", {})

        xml_output = json_to_xml(data_json)

        # Determine the file path
        file_path = os.path.join(os.path.dirname(__file__), folder_path, file_name)

        # Ensure the directory exists
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        try:
            with open(file_path, "w", encoding="utf-8") as file:
                file.write(xml_output)

            return Response(
                {"message": "File saved successfully!"}, status=status.HTTP_201_CREATED
            )

        except Exception as e:
            # Handle exceptions and return a response with error message
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


def json_to_xml(json_data):
    root = ET.Element("JOB", VERSION="2.0")

    # Process nodes
    for node in json_data["nodes"]:
        module = ET.SubElement(
            root,
            "MOUDLE",
            status="true",
            name=node["type"].capitalize(),
            VERSION="1.01",
        )
        for key, value in node["properties"].items():
            parameter = ET.SubElement(
                module,
                "PARAMETER",
                VALID="TRUE",
                name=key.replace('_', ' '),
                uiname=key.replace('_', ' '),
                tag="TRUE",
            )
            parameter.text = str(value)

    # Add JOBINFORMATION section
    job_info = ET.SubElement(root, "JOBINFORMATION")
    ET.SubElement(job_info, "PROJECT").text = json_data["project"]
    ET.SubElement(job_info, "SURVEY").text = json_data["survey"]
    ET.SubElement(job_info, "LINE")
    ET.SubElement(job_info, "USER")
    ET.SubElement(job_info, "HOSTNAME")
    ET.SubElement(job_info, "DBNAME").text = json_data["dbname"]
    ET.SubElement(job_info, "DBUSER")
    ET.SubElement(job_info, "DBPWD")

    # Add VARDEFINE section
    var_define = ET.SubElement(root, "VARDEFINE", TYPE="Cross Unit", ITERATOR="1")
    col_header = ET.SubElement(var_define, "COLHEADER")
    ET.SubElement(
        col_header, "VARCOL", VARTYPE="VARIABLE", TYPE="String", DEFVALUE=""
    ).text = "_UNIT_1234_LINE"
    ET.SubElement(
        col_header, "VARCOL", VARTYPE="VARIABLE", TYPE="String", DEFVALUE=""
    ).text = "Job Name"
    var_table = ET.SubElement(var_define, "VARTABLE")
    row = ET.SubElement(var_table, "ROW")
    ET.SubElement(row, "COL")
    ET.SubElement(row, "COL")

    # Create a dictionary for quick node lookup by ID
    node_id_map = {node["id"]: idx + 1 for idx, node in enumerate(json_data["nodes"])}

    # Process edges and add PLOT section
    plot = ET.SubElement(root, "PLOT")
    for idx, node in enumerate(json_data["nodes"], start=1):
        pom = ET.SubElement(plot, "POM", IDX=str(idx), ID=str(idx))
        rect = ET.SubElement(pom, "RECT")
        ET.SubElement(rect, "X").text = str(node["x"])
        ET.SubElement(rect, "Y").text = str(node["y"])

        # Find edges where the current node is the target
        prev_edges = [
            edge for edge in json_data["edges"] if edge["targetNodeId"] == node["id"]
        ]
        if prev_edges:
            prev = ET.SubElement(pom, "PREV")
            for edge in prev_edges:
                prev_node_idx = node_id_map[edge["sourceNodeId"]]
                prev_item = ET.SubElement(
                    prev, "ITEM", CHANNLE="0", ID=str(prev_node_idx)
                )
                prev_item.text = "0"

    xml_str = ET.tostring(root, encoding="utf-8")
    parsed_xml = minidom.parseString(xml_str)
    pretty_xml_as_string = parsed_xml.toprettyxml(indent="\t")

    # Replace the default XML declaration with the required one
    pretty_xml_as_string = pretty_xml_as_string.replace(
        '<?xml version="1.0" ?>', '<?xml version="1.0" encoding="UTF-8"?>'
    )

    return pretty_xml_as_string


class DelJobView(APIView):
    def post(self, request):
        file_name = request.data.get("file_name")
        folder_path = request.data.get("folder_path")
        if not file_name or not folder_path:
            return Response(
                {"error": "File name and folder path are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        file_path = os.path.join(folder_path, file_name)

        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                return Response(
                    {"success": "File deleted successfully."}, status=status.HTTP_200_OK
                )
            except Exception as e:
                return Response(
                    {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        else:
            return Response(
                {"error": "File not found."}, status=status.HTTP_404_NOT_FOUND
            )
import subprocess
from django.http import HttpResponse
class RunJobView(View):
    @method_decorator(csrf_exempt)
    def post(self, request):
        import json
        data = json.loads(request.body)
        filename = data.get('filename')
        # 监控文件夹下的文件
        result = ''
        folder_path = "/u1/GeoEast/ieco1.6.2/libso/batp/mod"
        jobsh = folder_path+"/djob"
        jobname = folder_path+"/"+filename      
        # # 切换用户并运行命令
        try:
            # 切换到用户geoeast并执行命令
            command = "sudo su - geoeast -c '/u1/GeoEast/ieco1.6.2/libso/batp/mod djob demo530.job'"
            
            # 执行命令并捕获输出
            process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = process.communicate()

            if process.returncode == 0:
                return HttpResponse(f"Command executed successfully:\n{stdout.decode('utf-8')}")
            else:
                return HttpResponse(f"Error executing command:\n{stderr.decode('utf-8')}")
        except Exception as e:
            return HttpResponse(f"An error occurred: {str(e)}")

        # print(f'{jobsh} {jobname}')
        # os.system(f'{jobsh} {jobname}')
        # print("123")
        # folder_name = folder_path + f'/{filename}.*.list'

        # while not os.path.exists(folder_name):
        #     time.sleep(1)  # 等待文件生成

        # # 读取文件内容
        # with open(folder_name, 'r') as file:
        #     result = file.read()

        # return JsonResponse({'result': result})