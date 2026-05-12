# Khazar Emblem Generator — Hello

You're holding a small handmade clock. It draws a unique synthetic Khazar-style
sun-amulet on its e-paper screen every couple of minutes. Each minute of the
day has its own amulet — 14:23 today looks the same as 14:23 next year. The
piece is part of an art project called *Light The Same Fire*.

## What you need

- Power supply (USB-C → micro-USB, included)
- WiFi network for the room you put it in
- Your phone

## Setting it up

1. **Plug it in.** It'll start glowing, the screen will refresh a few times.
2. **Wait ~90 seconds.** It needs time to boot, look for known WiFi, and
   decide it doesn't know your network yet.
3. **On your phone, open WiFi settings.** Look for an open network called
   **`comitup-204`**. Tap it to connect — no password needed.
4. **A setup page should appear** automatically. If it doesn't, open any
   browser and visit `http://10.41.0.1` — that's the Pi.
5. **Pick your home WiFi** from the list, type the password, hit Save.

After about a minute the screen will refresh with a new amulet. You're done.

## What you'll see

Every couple of minutes the e-paper screen flickers briefly and a new amulet
appears. Each one:

- Has a small loop at the top (like a real pendant — you could thread a cord
  through it)
- Has a round frame, sometimes with extra decorations on the edge
- Has spokes, petals, or other patterns radiating from the center
- Has a small charge or symbol in the middle

The flicker is normal — that's how e-paper redraws. The image will then sit
still for about two minutes before changing again.

## "Your" minute

The amulet for a particular minute is always the same. So you can pick a
minute that means something to you — your birthday, the time your kid was
born, the moment you and your partner met — and photograph the screen at
exactly that time. Tomorrow at the same minute, you'll see the same amulet.

## Moving it to a new place

If you take the clock somewhere with different WiFi (a new home, your
parents' place, a hotel), the setup flow repeats:

1. Plug it in at the new place.
2. Wait ~90 seconds.
3. Look for `comitup-204` on your phone, connect.
4. Pick the new WiFi in the setup page.

It remembers networks it has seen before, so going back home doesn't need
the setup flow again — it just rejoins automatically.

## When something looks wrong

**Screen is blank or stuck.** Try unplugging it, waiting 10 seconds, and
plugging it back in.

**Can't find `comitup-204` on your phone.** Make sure the Pi has been
running for at least 90 seconds since power-on. If it still doesn't appear,
unplug and replug.

**Screen shows the same amulet for too long.** Each amulet is meant to be
there for about 2 minutes. If it's been there 5+ minutes, the program may
have stopped. Power-cycle and it'll come back up.

## About

Built by **Nimrod Astarhan**.
- nimrod@astarhan.com
- nimrodastarhan.com

Part of the *Light The Same Fire* art project. Source code lives at
<https://github.com/nimast/khazar-emblem-generator>. If you're curious about
how it's made, or you want to know what minute corresponds to what amulet,
just ask.
