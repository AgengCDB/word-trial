import random
from english_words import get_english_words_set

from models import ThisRun, ThisTurn

WORDS = [w for w in get_english_words_set(['web2'], lower=True) if 5 <= len(w) <= 10]

def get_word():
    return random.choice(WORDS)

def get_info_screen(run: ThisRun):
    for word_to_match, colored_word, plus_score, minus_score in run.word_history[-10:]:
        print(f"{word_to_match:<20} {colored_word:<20} (\033[92m{plus_score}\033[0m \033[91m{minus_score}\033[0m)")
    
    print()
    print(f"Total score : {run.total_score} (\033[92m{run.plus_score}\033[0m \033[91m{run.minus_score}\033[0m)")

def get_this_turn_score(turn: ThisTurn):
    turn.plus_score = 0
    turn.minus_score = 0
    result = []

    longest = max(len(turn.word_to_match), len(turn.user_input))
    for i in range(longest):
        char_match = turn.word_to_match[i] if i < len(turn.word_to_match) else None
        char_input = turn.user_input[i] if i < len(turn.user_input) else None

        if char_input == char_match and char_input is not None:
            result.append(f"\033[92m{char_input}\033[0m")   # green
            turn.plus_score += 1
        else:
            wrong_char = char_input if char_input is not None else char_match
            result.append(f"\033[91m{wrong_char}\033[0m")
            turn.minus_score -= 1

    turn.total_score = turn.plus_score + turn.minus_score
    turn.colored_word = "".join(result)
    print(turn.colored_word, turn.plus_score, turn.minus_score)

def get_total_score(run: ThisRun, turn: ThisTurn):
    run.plus_score += turn.plus_score
    run.minus_score += turn.minus_score
    run.total_score = run.plus_score + run.minus_score

def main():
    print("start main.py")

    run = ThisRun("player1")

    i = 0
    while True:
        i += 1
        print(f"\n=== Turn {i} ===")
        turn = ThisTurn(i)

        turn.word_to_match = get_word()
        get_info_screen(run)
        
        print()
        print(f"Word to match : {turn.word_to_match}")
        turn.user_input = input("Input         : ")

        get_this_turn_score(turn)
        get_total_score(run, turn)

        run.word_history.append((turn.word_to_match, turn.colored_word, turn.plus_score, turn.minus_score))
        
        #### Reset
        turn.reset()

if __name__ == "__main__":
    main()
