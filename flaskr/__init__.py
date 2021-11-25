import os
from flask import Flask, request, abort, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
import random
from models import db, setup_db, Question, Category

QUESTIONS_PER_PAGE = 10

def paginate_questions(request, selection):
    items_limit = request.args.get('limit', 10, type=int)
    selected_page = request.args.get('page', 1, type=int)
    current_index = selected_page - 1

    questions = Question.query.order_by(Question.id).limit(items_limit).\
        offset(current_index * items_limit).all()

    current_questions = [question.format() for question in questions]

    return current_questions

def create_app(test_config=None):
    # create and configure the app
    app = Flask(__name__)
    setup_db(app)
    CORS(app)

    # Using the after_request decorator to set Access-Control-Allow

    @app.after_request
    def after_request(response):
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers',
                             'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Method',
                             'GET,PUT,POST,DELETE,PATCH')
        return response

    # Creating an endpoint to handle GET requests for all available categories.
    @app.route('/categories', methods=['GET'])
    def retrieve_categories():
        categories = Category.query.all()
        categories_dict = {}
        for category in categories:
            categories_dict[category.id] = category.type

        if (len(categories_dict) == 0):
            abort(404)

        return jsonify({
         'success': True,
         "categories": {category.id: category.type for category in categories}
          })

    # Creating  an endpoint to handle GET requests for questions,
    # including pagination (every 10 questions).
    # This endpoint  returns a list of questions,
    # number of total questions, current category, categories
    @app.route('/api/v1.0/questions', methods=['GET'])
    def get_questions():
        selection = Question.query.order_by(Question.id)
        current_questions = paginate_questions(request, selection)

        categories = Category.query.order_by(Category.type).all()
        categories = {category.id: category.type for category in categories}

        if len(current_questions) == 0:
            abort(404)

        return jsonify({
            "success": True,
            "questions": current_questions,
            "total_questions": selection.count(),
            "categories": categories,
            "current_category": None
        })

    #  Creating an endpoint to handle DELETE requests using a question ID
    @app.route('/api/v1.0/questions/<int:question_id>', methods=['DELETE'])
    def delete_question(question_id):
        try:
            question = Question.query.get_or_404(question_id)
            question_id = question.id
            question.delete()

            questions = Question.query.order_by(Question.id)
            current_questions = paginate_questions(request, questions)

            return jsonify({
                'success': True,
                'deleted': question_id,
                'questions': current_questions,
                'total_questions': len(questions.all())
            })
        except:
            abort(422)
    # Creating  an endpoint to POST a new question,
    # which will require the question and answer text,
    # category, and difficulty score.

    @app.route('/api/v1.0/questions', methods=['POST'])
    def add_question():
        body = request.get_json()

        new_question = body.get('question', None)
        new_answer = body.get('answer', None)
        new_difficulty = body.get('difficulty', None)
        new_category = body.get('category', None)

        if not \
           (new_question and new_answer and new_difficulty and new_category):
            abort(422)

        try:
            question = Question(
                question=new_question,
                answer=new_answer,
                difficulty=new_difficulty,
                category=new_category
            )
            question.insert()

            return jsonify({
                'success': True,
                'created': question.id,
            })

        except Exception as ex:
            print(str(ex))
            abort(422)

    # Creating a POST endpoint to get questions based on a search term.
    # It returns any questions for whom the search term
    # is a substring of the question.
    @app.route('/api/v1.0/questions/search', methods=['POST'])
    def search_question():
        search_request = request.get_json()
        search_term = search_request["searchTerm"]
        query_term = "%%" + search_term + "%%"
        query_result = db.session.query(Question).filter(
            Question.question.ilike(query_term)).all()
        total_number_of_questions = len(query_result)
        if total_number_of_questions == 0:
            abort(404)

        response = {
            "questions": [],
            "total_questions": total_number_of_questions,
            "current_category": None}
        for question in query_result:
            response["questions"].append({'id': question.id,
                                          'question': question.question,
                                          'answer': question.answer,
                                          'difficulty': question.difficulty,
                                          'category': question.category
                                          })
        return jsonify(response)

    # Creating  a GET endpoint to get questions based on category.

    @app.route('/api/v1.0/categories/<int:category_id>/questions',
               methods=['GET'])
    def questions_by_category(category_id):
        try:
            question_query = Question.query.filter(
                Question.category == category_id)
            total_questions = question_query.count()
            category_query = Category.query.get(category_id)
            category_string = category_query.type
            response = {
                "questions": [],
                "total_questions": total_questions,
                "current_category": category_string}
            for question in question_query:
                response["questions"].append({'id': question.id,
                                              'question': question.question,
                                              'answer': question.answer,
                                              'difficulty': question.difficulty,
                                              'category': question.category
                                              })
            return jsonify(response)
        except BaseException:
            abort(404)

    # Creating a POST endpoint to get questions to play the quiz.
    # This endpoint should take category and previous question parameters
    # and return a random questions within the given category,
    # if provided, and that is not one of the previous questions
    @app.route('/api/v1.0/quizzes', methods=['POST'])
    def play_quiz():
        try:
            body = request.get_json()
            quiz_category = body.get('quiz_category', None)
            previous_questions = body.get('previous_questions', [])

            categories_id = quiz_category['id']
            current_category = Category.query.filter_by(id=categories_id).all()

            if current_category is None:
                abort(422)

            if categories_id == 0:
                questions = Question.query.order_by(Question.id).all()
            else:
                questions = Question.query.filter_by(
                    category=str(categories_id)).order_by(Question.id).all()

            if len(questions) == 0:
                abort(422)

            collected_questions = []
            for item in questions:
                if item.id not in previous_questions:
                    collected_questions.append(item.format())

            if len(collected_questions) == 0:

                return jsonify({
                    'success': True,
                    'message': 'No more questions',
                    'totalQuestions': len(questions)
                    })

            else:
                current_question = random.choice(collected_questions)
                previous_questions.append(current_question['id'])

                return jsonify({
                  'success': True,
                  'question': current_question
                })
        except:
            abort(422)
    # Creating  error handlers for all expected errors
    # Including 404 and 422.

    @app.errorhandler(404)
    def not_found(error):
        return jsonify({
            "success": False,
            "error": 404,
            "message": "resource not found"
        }), 404

    @app.errorhandler(400)
    def bad_request(error):
        return jsonify({
          'success': False,
          'message': 'bad request',
          'error': 400
        }), 400
    
    @app.errorhandler(422)
    def unprocessable(error):
        return (
         jsonify({"success": False, "error": 422, "message": "unprocessable"}),
         422,
         )
    @app.errorhandler(500)
    def internal_server_error(error):
        return jsonify({
            'success': False,
            'error': 500,
            'message': 'Internal Server Error'
        }), 500    
    return app
