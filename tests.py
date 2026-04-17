#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Teambition API 工具 - 测试文件
"""

import unittest
from unittest.mock import Mock, patch
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import TeambitionAPI, get_api_client, to_excel, DEFAULT_API_CONFIGS, _api_result_list, resolve_param
import pandas as pd


class TestTeambitionAPI(unittest.TestCase):
    """测试 TeambitionAPI 类"""

    def setUp(self):
        """测试前准备"""
        self.api = TeambitionAPI("test_token", "test_tenant_id")

    def test_init(self):
        """测试初始化"""
        self.assertEqual(self.api.token, "test_token")
        self.assertEqual(self.api.tenant_id, "test_tenant_id")
        self.assertEqual(self.api.BASE_URL, "https://open.teambition.com/api")

    def test_get_headers(self):
        """测试获取请求头"""
        headers = self.api._get_headers()
        expected_headers = {
            "Authorization": "Bearer test_token",
            "X-Tenant-type": "organization",
            "X-Tenant-Id": "test_tenant_id"
        }
        self.assertEqual(headers, expected_headers)

    @patch('app.requests.request')
    def test_request_success(self, mock_request):
        """测试成功请求"""
        mock_response = Mock()
        mock_response.json.return_value = {"code": 200, "result": {"test": "data"}}
        mock_request.return_value = mock_response

        result = self.api._request("GET", "/test/endpoint")

        self.assertEqual(result, {"code": 200, "result": {"test": "data"}})
        mock_request.assert_called_once()

    @patch('app.requests.request')
    def test_request_error(self, mock_request):
        """测试请求错误"""
        mock_response = Mock()
        mock_response.json.return_value = {"code": 400, "errorMessage": "Bad Request"}
        mock_request.return_value = mock_response

        with self.assertRaises(Exception) as context:
            self.api._request("GET", "/test/endpoint")

        self.assertIn("API 错误", str(context.exception))

    @patch('app.requests.request')
    @patch('app.st.session_state')
    def test_call_search_project_stages_no_duplicate_project_in_query(self, mock_session, mock_request):
        """stage/search：projectId 仅在路径中，query 不应重复 projectId / project_id。"""
        mock_session.get.return_value = DEFAULT_API_CONFIGS
        mock_response = Mock()
        mock_response.json.return_value = {"code": 200, "result": []}
        mock_request.return_value = mock_response

        pid = "69dda1ad6cb8d6136c5720e7"
        self.api.call("search_project_stages", project_id=pid)

        mock_request.assert_called_once()
        args, kwargs = mock_request.call_args
        self.assertEqual(
            args[1],
            f"https://open.teambition.com/api/v3/project/{pid}/stage/search",
        )
        self.assertEqual(kwargs.get("params"), {"pageSize": 50})

    @patch('app.requests.request')
    @patch('app.st.session_state')
    def test_get_org_info(self, mock_session, mock_request):
        """测试获取企业信息 (新 dynamic path)"""
        mock_session.get.return_value = DEFAULT_API_CONFIGS  # mock configs
        mock_response = Mock()
        mock_response.json.return_value = {"code": 200, "result": {"name": "Test Org"}}
        mock_request.return_value = mock_response

        result = self.api.get_org_info()

        self.assertEqual(result, {"code": 200, "result": {"name": "Test Org"}})
        mock_request.assert_called_with("GET", "https://open.teambition.com/api/org/info", headers=self.api._get_headers(), params={})

    def test_resolve_query_tasks_filter_mutually_exclusive_with_task_ids(self):
        """官方文档 taskId 与 filter 模式互斥：有 task_ids 时不应生成 filter。"""
        self.assertIsNone(resolve_param("build_task_filter", {"task_ids": ["a", "b"]}))
        f = resolve_param("build_task_filter", {"project_id": "p1"})
        self.assertIn("p1", f)
        self.assertEqual(resolve_param("build_task_id_query_param", {"task_ids": ["a", "b"]}), "a,b")
        self.assertEqual(resolve_param("build_task_id_query_param", {"taskId": "single"}), "single")

    def test_api_result_list_null(self):
        """result 为 null 时须得到空列表，避免 NoneType 不可迭代。"""
        self.assertEqual(_api_result_list({"code": 200, "result": None}), [])
        self.assertEqual(_api_result_list({"code": 200}), [])
        self.assertEqual(_api_result_list({"result": [{"id": "1"}]}), [{"id": "1"}])
        self.assertEqual(_api_result_list({"result": {"id": "one"}}), [{"id": "one"}])

    @patch('app.requests.request')
    @patch('app.st.session_state')
    def test_search_project_stages_null_result(self, mock_session, mock_request):
        """接口返回 result: null 时阶段列表应为 []。"""
        mock_session.get.return_value = False
        mock_response = Mock()
        mock_response.json.return_value = {"code": 200, "result": None}
        mock_request.return_value = mock_response
        self.assertEqual(self.api.search_project_stages("proj_x"), [])

    @patch('app.requests.request')
    def test_get_projects(self, mock_request):
        """测试获取项目列表（游标分页，首包无 nextPageToken 即结束）"""
        mock_response = Mock()
        mock_response.json.return_value = {"code": 200, "result": [{"id": "1", "name": "Project 1"}]}
        mock_request.return_value = mock_response

        result = self.api.get_projects(page_size=10)

        self.assertEqual(result, [{"id": "1", "name": "Project 1"}])
        mock_request.assert_called_with("GET", "https://open.teambition.com/api/v3/project/query",
                                      headers=self.api._get_headers(), params={"pageSize": 10})

    @patch('app.requests.request')
    def test_get_projects_two_batches(self, mock_request):
        """第二包携带 pageToken，合并两页结果"""
        def make_resp(payload):
            m = Mock()
            m.json.return_value = payload
            return m

        mock_request.side_effect = [
            make_resp({"code": 200, "result": [{"id": "a"}], "nextPageToken": "tok2"}),
            make_resp({"code": 200, "result": [{"id": "b"}], "nextPageToken": None}),
        ]

        result = self.api.get_projects(page_size=10)

        self.assertEqual(result, [{"id": "a"}, {"id": "b"}])
        self.assertEqual(mock_request.call_count, 2)
        mock_request.assert_any_call(
            "GET", "https://open.teambition.com/api/v3/project/query",
            headers=self.api._get_headers(), params={"pageSize": 10},
        )
        mock_request.assert_any_call(
            "GET", "https://open.teambition.com/api/v3/project/query",
            headers=self.api._get_headers(), params={"pageSize": 10, "pageToken": "tok2"},
        )

    @patch('app.requests.request')
    def test_get_project_tasks(self, mock_request):
        """测试获取项目任务"""
        mock_response = Mock()
        mock_response.json.return_value = {"code": 200, "result": [{"id": "1", "name": "Task 1"}]}
        mock_request.return_value = mock_response

        result = self.api.get_project_tasks("project_123", page_size=20)

        self.assertEqual(result, [{"id": "1", "name": "Task 1"}])
        mock_request.assert_called_with(
            "GET",
            "https://open.teambition.com/api/v3/task/query",
            headers=self.api._get_headers(),
            params={"pageSize": 20, "filter": '{"projectId": "project_123"}'},
        )

    @patch('app.requests.request')
    def test_query_tasks_global_by_task_ids(self, mock_request):
        """全局 /v3/task/query：官方文档参数 taskId（逗号分隔）"""
        mock_response = Mock()
        mock_response.json.return_value = {"code": 200, "result": [{"id": "t1"}]}
        mock_request.return_value = mock_response

        tasks, next_token = self.api.query_tasks(task_ids=["a", "b"])

        self.assertEqual(tasks, [{"id": "t1"}])
        self.assertIsNone(next_token)
        mock_request.assert_called_with(
            "GET",
            "https://open.teambition.com/api/v3/task/query",
            headers=self.api._get_headers(),
            params={"taskId": "a,b"},
        )

    def test_query_tasks_global_requires_identifier(self):
        """全局查询未提供 task_ids / short_ids / parent_task_id 时应报错"""
        with self.assertRaises(ValueError):
            self.api.query_tasks()

    def test_query_tasks_global_taskid_parent_conflict(self):
        """taskId 与 parentTaskId 不可同时出现"""
        with self.assertRaises(ValueError):
            self.api.query_tasks(task_ids="x", parent_task_id="y")


class TestUtilityFunctions(unittest.TestCase):
    """测试工具函数"""

    def test_to_excel(self):
        """测试Excel导出功能"""
        df1 = pd.DataFrame({"col1": [1, 2], "col2": ["a", "b"]})
        df2 = pd.DataFrame({"col3": [3, 4], "col4": ["c", "d"]})

        result = to_excel([df1, df2], ["Sheet1", "Sheet2"])

        # 检查返回的是BytesIO对象
        self.assertIsInstance(result, pd.io.common.BytesIO)

        # 检查内容不为空（seek到末尾检查大小）
        result.seek(0, 2)  # 移动到文件末尾
        self.assertGreater(result.tell(), 0)

    @patch('app.st.session_state')
    def test_get_api_client_with_valid_data(self, mock_session):
        """测试获取API客户端 - 有有效数据"""
        mock_session.get.side_effect = lambda key, default='': {
            'token': 'test_token',
            'tenant_id': 'test_tenant'
        }.get(key, default)

        client = get_api_client()

        self.assertIsInstance(client, TeambitionAPI)
        self.assertEqual(client.token, 'test_token')
        self.assertEqual(client.tenant_id, 'test_tenant')

    @patch('app.st.session_state')
    def test_get_api_client_without_data(self, mock_session):
        """测试获取API客户端 - 无数据"""
        mock_session.get.return_value = ''

        client = get_api_client()

        self.assertIsNone(client)


if __name__ == '__main__':
    unittest.main()