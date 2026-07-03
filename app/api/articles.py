import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.schemas import ArticleCreateRequest, ArticleResponse, ArticleUpdateRequest
from app.database import get_db
from app.services.knowledge import KnowledgeService

router = APIRouter(prefix="/articles")


@router.get("", response_model=list[ArticleResponse])
def list_articles(db: Session = Depends(get_db)):
    svc = KnowledgeService(db)
    return svc.list_all()


@router.get("/{article_id}", response_model=ArticleResponse)
def get_article(article_id: uuid.UUID, db: Session = Depends(get_db)):
    svc = KnowledgeService(db)
    article = svc.get(article_id)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    return article


@router.post("", response_model=ArticleResponse, status_code=201)
def create_article(request: ArticleCreateRequest, db: Session = Depends(get_db)):
    svc = KnowledgeService(db)
    article = svc.create(request.title, request.body, request.category)
    db.commit()
    return article


@router.put("/{article_id}", response_model=ArticleResponse)
def update_article(article_id: uuid.UUID, request: ArticleUpdateRequest, db: Session = Depends(get_db)):
    svc = KnowledgeService(db)
    fields = {k: v for k, v in request.model_dump().items() if v is not None}
    if not fields:
        raise HTTPException(status_code=400, detail="No fields to update")
    article = svc.update(article_id, **fields)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    db.commit()
    return article


@router.delete("/{article_id}", status_code=204)
def delete_article(article_id: uuid.UUID, db: Session = Depends(get_db)):
    svc = KnowledgeService(db)
    if not svc.delete(article_id):
        raise HTTPException(status_code=404, detail="Article not found")
    db.commit()
