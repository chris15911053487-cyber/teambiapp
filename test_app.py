import os
import sys
from io import BytesIO

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

import pandas as pd
from app import TeambitionAPI, to_excel


def test_teambition_api_get_headers():
    api = TeambitionAPI(token="test_token", tenant_id="test_tenant")

    expected = {
        "Authorization": "Bearer test_token",
        "X-Tenant-type": "organization",
        "X-Tenant-Id": "test_tenant"
    }

    assert api._get_headers() == expected


def test_to_excel_returns_bytesio():
    df = pd.DataFrame({"col": [1, 2, 3]})
    excel_bytes = to_excel([df], ["Sheet1"])

    assert isinstance(excel_bytes, BytesIO)
    excel_bytes.seek(0, os.SEEK_END)
    assert excel_bytes.tell() > 0
