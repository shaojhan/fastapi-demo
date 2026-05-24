from fastapi import APIRouter

router = APIRouter(prefix='/workflows', tags=['workflow'])

@router.post('/create', operation_id='create_workflow')
async def create_workflow(request_body):
    return request_body