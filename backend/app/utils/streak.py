from datetime import date

def update_user_streak(user):
    today = date.today()
    if not user.last_active_date:
        user.streak_count = 1
        user.last_active_date = today
        return

    if user.last_active_date == today:
        return 

    delta_days = (today - user.last_active_date).days

    if delta_days == 1:
        # Normal consecutive day: increase streak
        user.streak_count += 1
        if user.streak_count % 3 == 0 and user.streak_freezes < 3:
            user.streak_freezes += 1
            
    elif delta_days > 1:
        missed_days = delta_days - 1
        if user.streak_freezes >= missed_days:
            # THM Logic: Consume freezes to bridge the gap
            user.streak_freezes -= missed_days
            
            # Increment the streak for TODAY's action
            user.streak_count += 1
            
            # Check if today's action just earned them a new freeze back!
            if user.streak_count % 3 == 0 and user.streak_freezes < 3:
                user.streak_freezes += 1
        else:
            # Out of freezes: streak resets to 1 for today's action
            user.streak_count = 1
            user.streak_freezes = 0 

    user.last_active_date = today