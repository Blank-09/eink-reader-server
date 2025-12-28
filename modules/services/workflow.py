import modules.services.database as db

from modules.kavita.client import kavita_client


class WorkflowManager:
    async def handle_input(self, button: str, event_type: str):
        state = db.get_state()
        mode = state["mode"]
        cursor = state["cursor_index"]

        # --- GLOBAL NAVIGATION (Up/Down in Lists) ---
        if mode != "READER":
            if button == "A":  # UP
                db.update_state({"cursor_index": max(0, cursor - 1)})
                return
            elif button == "B":  # DOWN
                # Note: In real app, clamp this to len(items_list) - 1
                db.update_state({"cursor_index": cursor + 1})
                return

        # --- CONTEXT SPECIFIC LOGIC ---
        if mode == "LIBRARIES":
            await self._handle_libraries(button, state)
        elif mode == "SERIES":
            await self._handle_series(button, state)
        elif mode == "BOOKS":
            await self._handle_books(button, state)
        elif mode == "READER":
            self._handle_reader(button, state, event_type)

    async def _handle_libraries(self, button, state):
        if button == "C":  # SELECT
            # Save selection and go deeper
            libraries = await kavita_client.get_libraries()
            cursor = state["cursor_index"]
            if cursor < len(libraries):
                selected_item = libraries[cursor]
                real_id = selected_item["id"]
                print(f"-> Selected Library: {selected_item['name']} (ID: {real_id})")

                db.update_state(
                    {"mode": "SERIES", "selected_library_id": real_id, "cursor_index": 0}
                )
        # D (Back) does nothing at root

    async def _handle_series(self, button, state):
        if button == "C":  # SELECT
            lib_id = state["selected_library_id"]
            items = await kavita_client.get_series(lib_id)
            cursor = state["cursor_index"]

            if cursor < len(items):
                selected_item = items[cursor]
                real_id = selected_item["id"]
                print(f"-> Selected Series: {selected_item['name']} (ID: {real_id})")

                db.update_state({"mode": "BOOKS", "selected_series_id": real_id, "cursor_index": 0})

        elif button == "D":  # BACK
            print("<- Back to Libraries")
            db.update_state(
                {
                    "mode": "LIBRARIES",
                    "cursor_index": 0,  # Reset or we could restore previous position
                }
            )

    async def _handle_books(self, button, state):
        if button == "C":  # SELECT
            series_id = state["selected_series_id"]
            items = await kavita_client.get_series_volumes(series_id)
            cursor = state["cursor_index"]

            if cursor < len(items):
                selected_item = items[cursor]
                real_id = selected_item["chapterId"]
                print(f"-> Opening Book: {selected_item['name']} (ID: {real_id})")

                db.update_state({"mode": "READER", "selected_book_id": real_id, "current_page": 0})

        elif button == "D":  # BACK
            print("<- Back to Series")
            db.update_state({"mode": "SERIES", "cursor_index": 0})

    def _handle_reader(self, button, state, event_type):
        page = state["current_page"]
        step = state["scroll_step"]

        # --- SCROLLING (Fine Control) ---
        if button == "A":  # SCROLL UP
            # Decrement step. Server handles "Underflow" (going to prev page bottom)
            db.update_state({"scroll_step": step - 1})

        elif button == "B":  # SCROLL DOWN
            # Increment step. Server handles "Overflow" (going to next page top)
            db.update_state({"scroll_step": step + 1})

        # --- JUMPING (Page Control) ---
        elif button == "F":  # NEXT PAGE (Direct Jump)
            print("⏩ Jumping to Next Page")
            db.update_state(
                {
                    "current_page": page + 1,
                    "scroll_step": 0,  # Always start at the top
                }
            )

        elif button == "C":  # PREV PAGE (Direct Jump)
            print("⏪ Jumping to Previous Page")
            db.update_state(
                {
                    "current_page": max(0, page - 1),
                    "scroll_step": 0,  # Start at top (or -1 if you prefer bottom)
                }
            )

        # --- SYSTEM ---
        elif button == "D":  # BACK TO LIST
            db.update_state({"mode": "BOOKS", "cursor_index": 0})

        elif button == "E":  # MENU / SETTINGS
            if event_type == "single":
                new_orient = 1 if state["orientation"] == 0 else 0
                db.update_state({"orientation": new_orient})
            elif event_type == "hold":
                new_dither = "FLOYD" if state["dither_mode"] == "THRESHOLD" else "THRESHOLD"
                db.update_state({"dither_mode": new_dither})
