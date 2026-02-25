"""CLI application for the fitness coach."""

import asyncio
from datetime import date

import click
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table

from fitness_coach.adapters.sqlite_storage import SQLiteStorage
from fitness_coach.adapters.strava_client import StravaClient
from fitness_coach.adapters.strands_coach import StrandsCoach
from fitness_coach.config import get_settings
from fitness_coach.domain.athlete import Athlete, Goal, GoalType
from fitness_coach.ports.coach import CoachContext


console = Console()
settings = get_settings()


def get_storage() -> SQLiteStorage:
    return SQLiteStorage(settings.database_path)


def get_coach() -> StrandsCoach:
    return StrandsCoach(
        model=settings.ollama_model,
        host=settings.ollama_host,
    )


async def get_coach_context(storage: SQLiteStorage) -> CoachContext | None:
    athlete = await storage.get_default()
    if not athlete:
        return None

    schedule = await storage.get_active_for_athlete(athlete.id)
    recent_workouts = await storage.get_recent(athlete.id, count=10)

    return CoachContext(
        athlete=athlete,
        schedule=schedule,
        recent_workouts=recent_workouts,
    )


@click.group()
def cli():
    """Personal AI Fitness Coach - Your training companion."""
    pass


@cli.command()
@click.option("--seed", is_flag=True, help="Load pre-configured profile and schedule")
def setup(seed: bool):
    """Set up your athlete profile."""

    if seed:
        from fitness_coach.data.seed import seed_database

        console.print(Panel("Loading your profile and schedule...", title="Setup", style="blue"))
        asyncio.run(seed_database(settings.database_path))
        console.print("\n[green]Profile and schedule loaded![/green]")
        console.print("Run [bold]fitness-coach chat[/bold] to start talking with your coach.")
        return

    console.print(Panel("Let's set up your profile", title="Setup", style="blue"))

    name = Prompt.ask("What's your name?")
    birth_year = Prompt.ask("Birth year", default="1987")
    weight = Prompt.ask("Weight in kg", default="90")

    goal_desc = Prompt.ask(
        "What's your main fitness goal?",
        default="Weight loss through running, improve at bouldering",
    )

    notes = Prompt.ask(
        "Anything else I should know? (injuries, schedule constraints, etc.)",
        default="",
    )

    athlete = Athlete(
        id="default",
        name=name,
        date_of_birth=date(int(birth_year), 1, 1),
        weight_kg=float(weight),
        goals=[Goal(goal_type=GoalType.GENERAL_FITNESS, description=goal_desc)],
        notes=notes,
    )

    storage = get_storage()
    asyncio.run(storage.save(athlete))
    asyncio.run(storage.set_default(athlete.id))

    console.print(f"\n[green]Profile saved for {name}![/green]")
    console.print("Run [bold]fitness-coach chat[/bold] to start talking with your coach.")


@cli.command()
def profile():
    """View your current profile."""
    storage = get_storage()
    athlete = asyncio.run(storage.get_default())

    if not athlete:
        console.print("[yellow]No profile found. Run 'fitness-coach setup' first.[/yellow]")
        return

    table = Table(title="Your Profile", show_header=False)
    table.add_column("Field", style="cyan")
    table.add_column("Value")

    table.add_row("Name", athlete.name)
    table.add_row("Age", str(athlete.age) if athlete.age else "Not set")
    table.add_row("Weight", f"{athlete.weight_kg} kg" if athlete.weight_kg else "Not set")

    if athlete.goals:
        goals_str = "\n".join(f"• {g.description}" for g in athlete.goals)
        table.add_row("Goals", goals_str)

    if athlete.notes:
        table.add_row("Notes", athlete.notes[:200] + "..." if len(athlete.notes) > 200 else athlete.notes)

    console.print(table)


@cli.command()
def schedule():
    """View your current training schedule."""
    storage = get_storage()
    athlete = asyncio.run(storage.get_default())

    if not athlete:
        console.print("[yellow]No profile found. Run 'fitness-coach setup' first.[/yellow]")
        return

    sched = asyncio.run(storage.get_active_for_athlete(athlete.id))

    if not sched:
        console.print("[yellow]No schedule found.[/yellow]")
        return

    console.print(Panel(f"{sched.name}\n{sched.description}", title="Schedule", style="blue"))

    table = Table(title="Weekly Overview")
    table.add_column("Day", style="cyan")
    table.add_column("Type")
    table.add_column("Duration")
    table.add_column("Description")

    days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    workouts = sched.get_current_week_workouts()

    for workout in sorted(workouts, key=lambda w: w.day_of_week):
        table.add_row(
            days[workout.day_of_week],
            workout.workout_type.value,
            f"{workout.target_duration_minutes}min" if workout.target_duration_minutes else "-",
            workout.description[:40],
        )

    console.print(table)

    # Show today's workout in detail
    today = sched.get_today_workout()
    if today:
        console.print()
        console.print(Panel(
            f"[bold]{today.description}[/bold]\n\n{today.structured_workout or today.notes}",
            title="Today's Workout",
            style="green",
        ))


@cli.command()
def chat():
    """Chat with your fitness coach."""
    storage = get_storage()
    context = asyncio.run(get_coach_context(storage))

    if not context:
        console.print("[yellow]No profile found. Run 'fitness-coach setup' first.[/yellow]")
        return

    coach = get_coach()

    console.print(Panel(
        f"Hi {context.athlete.name}! I'm your fitness coach.\n"
        "Ask me anything about your training. Type 'quit' to exit.",
        title="Coach",
        style="green",
    ))

    while True:
        try:
            message = Prompt.ask("\n[bold blue]You[/bold blue]")

            if message.lower() in ("quit", "exit", "q"):
                console.print("[dim]See you next time! Keep moving.[/dim]")
                break

            if not message.strip():
                continue

            with console.status("[dim]Thinking...[/dim]"):
                response = asyncio.run(coach.chat(message, context))

            console.print()
            console.print(Panel(
                Markdown(response.message),
                title="Coach",
                style="green",
            ))

            # Save conversation
            asyncio.run(storage.save_message(context.athlete.id, "user", message))
            asyncio.run(storage.save_message(context.athlete.id, "assistant", response.message))

        except KeyboardInterrupt:
            console.print("\n[dim]See you next time![/dim]")
            break


@cli.command()
def briefing():
    """Get today's training briefing."""
    storage = get_storage()
    context = asyncio.run(get_coach_context(storage))

    if not context:
        console.print("[yellow]No profile found. Run 'fitness-coach setup' first.[/yellow]")
        return

    coach = get_coach()

    with console.status("[dim]Preparing your briefing...[/dim]"):
        response = asyncio.run(coach.get_daily_briefing(context))

    console.print(Panel(
        Markdown(response.message),
        title="Today's Briefing",
        style="blue",
    ))


@cli.command()
def auth():
    """Authenticate with Strava (OAuth flow)."""
    import webbrowser
    from fitness_coach.cli.auth import get_auth_url, run_callback_server, exchange_code_for_tokens

    if not settings.strava_client_id or not settings.strava_client_secret:
        console.print("[red]Missing Strava credentials![/red]")
        console.print("Add STRAVA_CLIENT_ID and STRAVA_CLIENT_SECRET to your .env file.")
        return

    console.print(Panel(
        "Starting Strava OAuth flow...\n\n"
        "1. Your browser will open Strava's authorization page\n"
        "2. Click 'Authorize' to grant access\n"
        "3. You'll be redirected back automatically",
        title="Strava Authentication",
        style="blue",
    ))

    auth_url = get_auth_url(settings.strava_client_id)
    console.print(f"\n[dim]Opening: {auth_url}[/dim]\n")

    webbrowser.open(auth_url)

    console.print("[dim]Waiting for authorization (timeout: 2 minutes)...[/dim]")

    try:
        code = run_callback_server(port=8000, timeout=120)

        if not code:
            console.print("[red]No authorization code received.[/red]")
            return

        console.print("[green]✓[/green] Authorization code received!")

        with console.status("[dim]Exchanging code for tokens...[/dim]"):
            tokens = asyncio.run(exchange_code_for_tokens(
                settings.strava_client_id,
                settings.strava_client_secret,
                code,
            ))

        console.print("[green]✓[/green] Tokens received!")
        console.print()
        console.print(Panel(
            f"Add these to your .env file:\n\n"
            f"STRAVA_ACCESS_TOKEN={tokens['access_token']}\n"
            f"STRAVA_REFRESH_TOKEN={tokens['refresh_token']}",
            title="Strava Tokens",
            style="green",
        ))

        # Also show athlete info
        athlete_info = tokens.get("athlete", {})
        if athlete_info:
            console.print(f"\n[dim]Authenticated as: {athlete_info.get('firstname')} {athlete_info.get('lastname')}[/dim]")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")


@cli.command()
@click.option("--full", is_flag=True, help="Sync full activity history (all pages)")
def sync(full: bool):
    """Sync workouts from Strava."""
    if not settings.strava_access_token:
        console.print("[yellow]Strava not configured. Run 'fitness-coach auth' first.[/yellow]")
        return

    storage = get_storage()
    athlete = asyncio.run(storage.get_default())

    if not athlete:
        console.print("[yellow]No profile found. Run 'fitness-coach setup' first.[/yellow]")
        return

    async def do_sync_recent():
        client = StravaClient(
            client_id=settings.strava_client_id,
            client_secret=settings.strava_client_secret,
            access_token=settings.strava_access_token,
            refresh_token=settings.strava_refresh_token,
        )

        try:
            activities = await client.get_activities(per_page=10)
            synced = 0

            for activity in activities:
                existing = await storage.get_by_strava_id(activity["id"])
                if not existing:
                    full_activity = await client.get_activity(activity["id"])
                    workout = client.activity_to_workout(full_activity, athlete.id)
                    await storage.save_workout(workout)
                    synced += 1
                    console.print(f"[green]✓[/green] {workout.name}")

            return synced
        finally:
            await client.close()

    async def do_full_sync():
        from fitness_coach.application.sync_all_activities import FullStravaSync

        client = StravaClient(
            client_id=settings.strava_client_id,
            client_secret=settings.strava_client_secret,
            access_token=settings.strava_access_token,
            refresh_token=settings.strava_refresh_token,
        )

        try:
            sync_use_case = FullStravaSync(client, storage)
            return await sync_use_case.execute(athlete.id, full=full)
        finally:
            await client.close()

    if full:
        console.print("[dim]Syncing full activity history from Strava...[/dim]")
        with console.status("[dim]This may take a while for large histories...[/dim]"):
            count = asyncio.run(do_full_sync())
    else:
        with console.status("[dim]Syncing from Strava...[/dim]"):
            count = asyncio.run(do_sync_recent())

    console.print(f"\n[green]Synced {count} new workout(s)[/green]")


@cli.command()
def workouts():
    """View recent workouts."""
    storage = get_storage()
    athlete = asyncio.run(storage.get_default())

    if not athlete:
        console.print("[yellow]No profile found. Run 'fitness-coach setup' first.[/yellow]")
        return

    recent = asyncio.run(storage.get_recent(athlete.id, count=10))

    if not recent:
        console.print("[dim]No workouts recorded yet.[/dim]")
        return

    table = Table(title="Recent Workouts")
    table.add_column("Date", style="cyan")
    table.add_column("Type")
    table.add_column("Duration")
    table.add_column("Distance")
    table.add_column("Pace")
    table.add_column("Avg HR")

    for w in recent:
        table.add_row(
            w.start_time.strftime("%a %d %b"),
            w.workout_type.value,
            f"{w.duration_minutes:.0f}min",
            f"{w.distance_km:.1f}km" if w.distance_km else "-",
            w.pace_formatted() or "-",
            f"{w.average_heartrate:.0f}" if w.average_heartrate else "-",
        )

    console.print(table)


@cli.command()
@click.option("--host", default="127.0.0.1", help="Host to bind the server to")
@click.option("--port", default=8080, help="Port to listen on")
def serve(host: str, port: int):
    """Start the web dashboard."""
    import uvicorn
    from fitness_coach.adapters.web.app import create_app

    console.print(f"[green]Starting dashboard at http://{host}:{port}/[/green]")
    uvicorn.run(create_app(), host=host, port=port)


def main():
    cli()


if __name__ == "__main__":
    main()
