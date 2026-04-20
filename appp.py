import streamlit as st
from blackjack import Bot, DealerBot, BasicStrategyH17Bot, Shoe, Hand

# ─── Game logic ──────────────────────────────────────────────────────────────
def run_shoe(bot, decks=2, balance=1000, h17=True,
             blackjack=1.5, rsa=True, das=True, surrender=True, max_rounds=50):

    log = []
    shoe = Shoe(decks=decks)
    balance_history = [balance]

    class G:
        pass
    game = G()
    game.h17 = h17
    game.das = das

    rounds = 0

    while shoe.play and rounds < max_rounds:
        rounds += 1
        h = bot.handNum(game)
        if h == 0:
            log.append("🚪 Bot wonged out.")
            break
        if balance < h:
            log.append("💸 Out of money.")
            break

        balance -= h
        log.append(f"--- Round {rounds} | Hands: {h} | Balance: {balance+h} ---")

        hands = []
        dealerHand = Hand(deck=shoe)
        for _ in range(h):
            hands.append(Hand(deck=shoe))
            hands[-1].addCard(0)
        dealerHand.addCard(0)
        for i in range(h):
            hands[i].addCard(0)
            log.append(f"  Hand {i+1}: {hands[i]}  ({hands[i].val()})")
        log.append(f"  Dealer shows: {dealerHand}")

        # Dealer blackjack checks
        if dealerHand.val() == 10 and shoe.shoe[0].val() == 1:
            shoe.deal(0)
            log.append("  Dealer blackjack!")
            for x in hands:
                if x.val() == 21: balance += 1
            balance_history.append(balance)
            continue
        if dealerHand.val() == 11 and shoe.shoe[0].val() == 10:
            shoe.deal(0)
            log.append("  Dealer blackjack!")
            for x in hands:
                if x.val() == 21: balance += 1
            balance_history.append(balance)
            continue

        # Play hands
        i = 0
        while i < len(hands):
            if len(hands[i].cards) == 1:
                hands[i].addCard(1)
            options = ['h', 's']
            if not (das and hands[i].hasBeenSplit):
                options.append('d')
            if surrender and not hands[i].hasBeenSplit and len(hands[i].cards) == 2:
                options.append('l')
            if len(hands[i].cards) >= 2 and hands[i].cards[0].rank == hands[i].cards[1].rank:
                if not (not rsa and hands[i].cards[1].val() == 1):
                    options.append('v')

            while len(options) > 0:
                if hands[i].val() > 21:
                    log.append(f"    Hand {i+1}: {hands[i]} → Bust")
                    hands.pop(i); i -= 1; break
                if hands[i].val() == 21:
                    if len(hands[i].cards) == 2:
                        log.append(f"    Hand {i+1}: {hands[i]} → Blackjack! +{1+blackjack}")
                        balance += 1 + blackjack
                        hands.pop(i); i -= 1
                    options = []; break

                c = bot.decision(options, hands[i], dealerHand)
                log.append(f"    Hand {i+1} ({hands[i].val()}) vs dealer {dealerHand.val()} → {c.upper()}")

                if c == 'h':
                    hands[i].addCard(1); options = ['h','s']
                elif c == 's':
                    options = []
                elif c == 'd':
                    balance -= 1; hands[i].addCard(1)
                    hands[i].double = True
                    log.append(f"    After double: {hands[i]} ({hands[i].val()})")
                    if hands[i].val() > 21:
                        log.append(f"    Hand {i+1}: Bust after double")
                        hands.pop(i); i -= 1
                    options = []
                elif c == 'v':
                    balance -= 1
                    new_hand = Hand(deck=shoe, cards=[hands[i].cards.pop(1)], hasBeenSplit=True)
                    hands[i].hasBeenSplit = True
                    hands.insert(i, new_hand); i -= 1
                    options = []
                elif c == 'l':
                    balance += 0.5
                    log.append(f"    Hand {i+1}: Surrender → +0.5")
                    hands.pop(i); i -= 1; options = []
            i += 1

        # Dealer plays
        dealerHand.addCard(0)
        if len(hands) > 0:
            while dealerHand.val() <= 16 or (dealerHand.val() == 17 and h17 and dealerHand.isSoft):
                dealerHand.addCard(0)
        log.append(f"  Dealer final: {dealerHand} ({dealerHand.val()})")

        if dealerHand.val() > 21:
            log.append("  Dealer busts! All remaining hands win.")
            for j, hand in enumerate(hands):
                won = 4 if hand.double else 2
                balance += won
                log.append(f"    Hand {j+1}: Win +{won}")
        else:
            for j, hand in enumerate(hands):
                if hand.val() > dealerHand.val():
                    won = 4 if hand.double else 2
                    balance += won
                    log.append(f"    Hand {j+1}: Win +{won}")
                elif hand.val() < dealerHand.val():
                    log.append(f"    Hand {j+1}: Loss")
                else:
                    push = 2 if hand.double else 1
                    balance += push
                    log.append(f"    Hand {j+1}: Push +{push}")

        balance_history.append(balance)

    log.append(f"\n✅ Shoe complete. Final balance: {balance} | Profit: {balance - balance_history[0]}")
    return log, balance_history


# ─── Streamlit UI ─────────────────────────────────────────────────────────────
st.set_page_config(page_title="Blackjack Bot Runner", layout="wide")
st.title("🃏 Blackjack Bot Runner")

col1, col2 = st.columns([1, 2])

with col1:
    st.subheader("Settings")
    bot_choice = st.selectbox("Bot", ["Random Bot", "Dealer Bot", "Basic Strategy Bot"])
    decks = st.slider("Decks", 1, 8, 2)
    starting_balance = st.number_input("Starting Balance", value=1000, step=100)
    max_rounds = st.slider("Max Rounds per Shoe", 10, 200, 50)
    h17 = st.checkbox("Dealer hits soft 17", value=True)
    das = st.checkbox("Double after split", value=True)
    rsa = st.checkbox("Re-split aces", value=True)
    surrender = st.checkbox("Surrender allowed", value=True)
    bj_payout = st.selectbox("Blackjack payout", ["3:2", "6:5"])
    blackjack = 1.5 if bj_payout == "3:2" else 1.2

    run = st.button("▶ Run Shoe", use_container_width=True)

with col2:
    st.subheader("Output")
    if run:
        if bot_choice == "Random Bot":
            bot = Bot()
        elif bot_choice == "Dealer Bot":
            bot = DealerBot()
        else:
            bot = BasicStrategyH17Bot(das=das)

        log, balance_history = run_shoe(
            bot=bot, decks=decks, balance=starting_balance,
            h17=h17, blackjack=blackjack, rsa=rsa, das=das,
            surrender=surrender, max_rounds=max_rounds
        )

        profit = balance_history[-1] - balance_history[0]
        m1, m2, m3 = st.columns(3)
        m1.metric("Starting Balance", f"${balance_history[0]}")
        m2.metric("Final Balance", f"${balance_history[-1]:.1f}")
        m3.metric("Profit", f"${profit:.1f}", delta=f"${profit:.1f}")

        st.line_chart(balance_history)

        with st.expander("📋 Full Hand Log", expanded=True):
            st.text("\n".join(log))
