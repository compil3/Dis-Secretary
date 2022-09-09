import asyncio
import copy
import enum
import math
import random
from typing import List

from naff import Extension
from naff.models import (
    ButtonStyles,
    Button,
    ComponentContext,
    InteractionContext,
    spread_to_rows,
    component_callback,
    get_components_ids,
    slash_command,
)


class GameState(enum.IntEnum):
    empty = 0
    player = -1
    ai = +1


def determine_board_state(components: list) -> List[list]:
    """
    Extrapolate the current state of the game based on the components of a message
    :param components: The components object from a message
    :return: The test_board state
    :rtype: list[list]
    """
    board = copy.deepcopy(BoardTemplate)
    for i in range(3):
        for x in range(3):
            button = components[i].components[x]
            if button.style == 2:
                board[i][x] = GameState.empty
            elif button.style == 1:
                board[i][x] = GameState.player
            elif button.style == 4:
                board[i][x] = GameState.ai
    return board


def render_board(board: list, disable=False) -> list:
    """
    Converts the test_board into a visual representation using discord components
    :param board: The game test_board
    :param disable: Disable the buttons on the test_board
    :return: List[action-rows]
    """
    buttons = []
    for i in range(3):
        for x in range(3):
            if board[i][x] == GameState.empty:
                style = ButtonStyles.GREY
            elif board[i][x] == GameState.player:
                style = ButtonStyles.BLURPLE
            else:
                style = ButtonStyles.RED
            buttons.append(
                Button(
                    style=style,
                    label="‎",
                    custom_id=f"tic_tac_toe_button||{i},{x}",
                    disabled=disable,
                )
            )
    return spread_to_rows(*buttons, max_in_row=3)


def determine_win_state(board: list, player: GameState) -> bool:
    """
    Determines if the specified player has won
    :param board: The game test_board
    :param player: The player to check for
    :return: bool, have they won
    """
    win_states = [
        [board[0][0], board[0][1], board[0][2]],
        [board[1][0], board[1][1], board[1][2]],
        [board[2][0], board[2][1], board[2][2]],
        [board[0][0], board[1][0], board[2][0]],
        [board[0][1], board[1][1], board[2][1]],
        [board[0][2], board[1][2], board[2][2]],
        [board[0][0], board[1][1], board[2][2]],
        [board[2][0], board[1][1], board[0][2]],
    ]
    return [player, player, player] in win_states


def determine_possible_positions(board: list) -> list[list[int]]:
    """
    Determines all the possible positions in the current game state
    :param board: The game test_board
    :return: A list of possible positions
    """
    possible_positions = []
    for i in range(3):
        possible_positions.extend(
            [i, x] for x in range(3) if board[i][x] == GameState.empty
        )

    return possible_positions


def evaluate(board):
    if determine_win_state(board, GameState.ai):
        return +1
    elif determine_win_state(board, GameState.player):
        return -1
    else:
        return 0


def min_max(test_board: list, depth: int, player: GameState):
    best = [-1, -1, -math.inf] if player == GameState.ai else [-1, -1, +math.inf]
    if (
        depth == 0
        or determine_win_state(test_board, GameState.player)
        or determine_win_state(test_board, GameState.ai)
    ):
        score = evaluate(test_board)
        return [-1, -1, score]

    for cell in determine_possible_positions(test_board):
        x, y = cell[0], cell[1]
        test_board[x][y] = player
        score = min_max(test_board, depth - 1, -player)
        test_board[x][y] = GameState.empty
        score[0], score[1] = x, y

        if (
            player == GameState.ai
            and score[2] > best[2]
            or player != GameState.ai
            and score[2] < best[2]
        ):
            best = score
    return best


BoardTemplate = [[0, 0, 0], [0, 0, 0], [0, 0, 0]]


class TicTacToe(Extension):
    @slash_command(
        name="tic_tac_toe",
        sub_cmd_name="start",
        sub_cmd_description="Start a game of tic tac toe",
    )
    async def ttt_start(self, ctx: InteractionContext):
        await ctx.send(
            content=f"{ctx.author.mention}'s tic tac toe game",
            components=render_board(copy.deepcopy(BoardTemplate)),
        )

    @staticmethod
    def determine_board_state(components: list):
        board = []
        for i in range(3):
            row = components[i]["components"]
            for button in row:
                if button["style"] == 2:
                    board.append(GameState.empty)
                elif button["style"] == 1:
                    board.append(GameState.player)
                elif button["style"] == 4:
                    board.append(GameState.ai)

        return board

    @component_callback(
        get_components_ids(render_board(board=copy.deepcopy(BoardTemplate)))  # type: ignore
    )
    async def process_turn(self, ctx: ComponentContext):
        await ctx.defer(edit_origin=True)
        try:
            async for user in ctx.message.mention_users:
                if ctx.author.id != user.id:
                    return
        except Exception as ex:
            print(ex)
            breakpoint()
            return
        button_pos = (ctx.custom_id.split("||")[-1]).split(",")
        button_pos = [int(button_pos[0]), int(button_pos[1])]
        components = ctx.message.components

        _board = determine_board_state(components)

        if _board[button_pos[0]][button_pos[1]] != GameState.empty:
            return

        _board[button_pos[0]][button_pos[1]] = GameState.player
        if not determine_win_state(_board, GameState.player):
            possible_positions = determine_possible_positions(_board)
            # ai pos
            if len(possible_positions) != 0:
                depth = len(possible_positions)

                move = await asyncio.to_thread(
                    min_max,
                    copy.deepcopy(_board),
                    min(random.choice([4, 6]), depth),
                    GameState.ai,
                )
                x, y = move[0], move[1]
                _board[x][y] = GameState.ai
        if determine_win_state(_board, GameState.player):
            winner = ctx.author.mention
        elif determine_win_state(_board, GameState.ai):
            winner = self.bot.user.mention
        elif len(determine_possible_positions(_board)) == 0:
            winner = "Nobody"
        else:
            winner = None

        _board = render_board(_board, disable=winner is not None)

        await ctx.edit_origin(
            content=f"{winner} has won!"
            if winner
            else f"{ctx.author.mention}'s tic tac toe game",
            components=spread_to_rows(*_board, max_in_row=3),
        )


def setup(bot):
    TicTacToe(bot)
