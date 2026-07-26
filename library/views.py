import json
from django.http import JsonResponse, HttpResponseNotAllowed
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import get_object_or_404
from .models import Book, Author

# ==========================================
# 1. READ ALL (GET) & CREATE (POST)
# ==========================================
@csrf_exempt
def book_list_or_create(request):
    if request.method == "GET":
        books = Book.objects.all()
        data = [{
            "id": b.id,
            "title": b.title,
            "author": b.author.name,
            "isbn": b.isbn,
            "published_date": str(b.published_date)
        } for b in books]
        return JsonResponse({"books": data}, status=200)

    elif request.method == "POST":
        try:
            body = json.loads(request.body)
            # Find the author object using the provided author ID
            author_obj = Author.objects.get(id=body["author_id"])
            
            # Create and save the new book record
            new_book = Book.objects.create(
                title=body["title"],
                author=author_obj,
                isbn=body["isbn"],
                published_date=body["published_date"]
            )
            return JsonResponse({
                "message": "Book created successfully!",
                "id": new_book.id
            }, status=201)
            
        except (ValueError, KeyError, Author.DoesNotExist) as e:
            return JsonResponse({"error": "Invalid data or Author ID not found"}, status=400)

    return HttpResponseNotAllowed(["GET", "POST"])


# ==========================================
# 2. READ ONE (GET), UPDATE (PUT), DELETE (DELETE)
# ==========================================
@csrf_exempt
def book_detail(request, book_id):
    # Automatically returns a 404 response if the book_id is missing from the database
    book = get_object_or_404(Book, id=book_id)

    if request.method == "GET":
        return JsonResponse({
            "id": book.id,
            "title": book.title,
            "author": book.author.name,
            "isbn": book.isbn,
            "published_date": str(book.published_date)
        }, status=200)

    elif request.method == "PUT":
        try:
            body = json.loads(request.body)
            
            # Update values if provided, otherwise keep existing data
            if "author_id" in body:
                book.author = Author.objects.get(id=body["author_id"])
            book.title = body.get("title", book.title)
            book.isbn = body.get("isbn", book.isbn)
            book.published_date = body.get("published_date", book.published_date)
            
            book.save()
            return JsonResponse({"message": "Book updated successfully!"}, status=200)
            
        except (ValueError, Author.DoesNotExist):
            return JsonResponse({"error": "Invalid data input or Author not found"}, status=400)

    elif request.method == "DELETE":
        book.delete()
        return JsonResponse({"message": "Book deleted successfully!"}, status=200)

    return HttpResponseNotAllowed(["GET", "PUT", "DELETE"])
