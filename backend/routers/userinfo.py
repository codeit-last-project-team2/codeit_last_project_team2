
import os
from fastapi import APIRouter, Depends, UploadFile, File
from backend.models.user_information_model import UserInformation, StoresRequest, StoreInfoRequest
from backend.services.userinformation_service import upload_store, update_store, store_names, store_info, delete_store
from backend.auth import get_current_user

from fastapi.staticfiles import StaticFiles


DATA_DIR = os.path.join("Data", "user_info")
DB_PATH = os.path.join(DATA_DIR, "database.db")

router = APIRouter(prefix="/userinfo", tags=["userinfo"])

@router.post("/upload")
def upload_store_info(req: UserInformation, user=Depends(get_current_user)):
    return upload_store(req)

@router.post("/update")
def upload_store_info(req: UserInformation, user=Depends(get_current_user)):
    return update_store(req)

@router.post("/get_store_names")
def get_store_name(req: StoresRequest):
    return store_names(req)

@router.post("/get_store_info")
def get_store_name(req: StoreInfoRequest):
    return store_info(req)

@router.post("/delete_store")
def get_store_name(req: StoreInfoRequest):
    return delete_store(req)


@router.post("/upload_image/{token}/{store_name}/menu/{menu_idx}")
async def upload_menu_image(
    token: str,
    store_name: str,
    menu_idx: int,
    file: UploadFile = File(...),
    user=Depends(get_current_user)   
):
    folder = os.path.join(DATA_DIR, token, store_name, "menus")
    os.makedirs(folder, exist_ok=True)

    _, ext = os.path.splitext(file.filename)
    filename = f"menu_{menu_idx}{ext}"
    save_path = os.path.join(folder, filename)

    with open(save_path, "wb") as f:
        f.write(await file.read())

    url_path = f"/static/{token}/{store_name}/menus/{filename}"
    return {"path": url_path}