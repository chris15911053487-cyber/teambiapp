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

from app import TeambitionAPI, get_api_client, to_excel
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
    def test_get_org_info(self, mock_request):
        """测试获取企业信息"""
        mock_response = Mock()
        mock_response.json.return_value = {"code": 200, "result": {"name": "Test Org"}}
        mock_request.return_value = mock_response

        result = self.api.get_org_info()

        self.assertEqual(result, {"code": 200, "result": {"name": "Test Org"}})
        mock_request.assert_called_with("GET", "https://open.teambition.com/api/org/info", headers=self.api._get_headers())

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
        mock_request.assert_called_with("GET", "https://open.teambition.com/api/v3/project/project_123/task/query",
                                      headers=self.api._get_headers(), params={"pageSize": 20})


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