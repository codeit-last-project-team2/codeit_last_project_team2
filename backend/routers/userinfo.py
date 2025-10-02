
import os
from fastapi import APIRouter, Depends
from backend.models.user_information_model import UserInformation, StoreInfoRequest
from backend.services.userinformation_service import upload_store, update_store, store_names, store_info, delete_store
from backend.auth import get_current_user

router = APIRouter(prefix="/userinfo", tags=["userinfo"])

@router.post("/upload")
def upload_store_info(req: UserInformation, user=Depends(get_current_user)):
    email = user["email"]
    return upload_store(req, email)

@router.post("/update")
def upload_store_info(req: UserInformation, user=Depends(get_current_user)):
    email = user["email"]
    return update_store(req, email)

@router.get("/get_store_names")
def get_store_name(user=Depends(get_current_user)):
    email = user["email"]
    return store_names(email)

@router.post("/get_store_info")
def get_store_name(req: StoreInfoRequest, user=Depends(get_current_user)):
    email = user["email"]
    return store_info(store_name=req.store_name, email=email)

@router.post("/delete_store")
def get_store_name(req: StoreInfoRequest, user=Depends(get_current_user)):
    email = user["email"]
    return delete_store(store_name=req.store_name, email=email)