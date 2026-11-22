within GeneratedInterfaces;
package GeneratedInterfaces
  connector Actuation
    Real channel_a;
    Real channel_b;
    Real channel_c;
  end Actuation;

  connector Orientation
    Real roll;
    Real pitch;
    Real yaw;
  end Orientation;

  connector Position
    Real x;
    Real y;
    Real z;
  end Position;

  connector StatusPacket
    Real speed;
    Integer health;
  end StatusPacket;

end GeneratedInterfaces;
